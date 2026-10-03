"""Password hashing, JWT issuance/verification, and symmetric encryption for secrets at rest.

This module has no FastAPI or database imports on purpose - it is pure crypto
plumbing. Request-scoped concerns (pulling the current user out of a token,
enforcing roles) live in app.api.deps instead.
"""

import enum
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# --- Password hashing -------------------------------------------------------
#
# bcrypt is pinned to <4.0 in requirements.txt: passlib 1.7.4 (last released in
# 2020 and effectively unmaintained) cannot detect bcrypt>=4.0's version info
# and raises MissingBackendError on the very first hash() call. Confirmed
# empirically against bcrypt 4.2/5.0 before landing on this pin.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt silently truncates/errors past 72 bytes; reject long passwords up
# front instead of letting that surprise show up later.
_MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > _MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {_MAX_PASSWORD_BYTES} bytes")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT access/refresh tokens -----------------------------------------------


class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenError(Exception):
    """Raised for any JWT that is malformed, expired, or not of the expected type."""


def _create_token(subject: str, token_type: TokenType, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(subject: str) -> str:
    return _create_token(subject, TokenType.ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))


def create_refresh_token(subject: str) -> str:
    return _create_token(subject, TokenType.REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def _decode_token(token: str, expected_type: TokenType) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise TokenError("Token is invalid or expired") from exc

    # Both token kinds are signed with the same secret, so without this check a
    # stolen refresh token could be replayed directly as an access token.
    if payload.get("type") != expected_type.value:
        raise TokenError(f"Expected a {expected_type.value} token, got {payload.get('type')!r}")
    return payload


def decode_access_token(token: str) -> dict:
    return _decode_token(token, TokenType.ACCESS)


def decode_refresh_token(token: str) -> dict:
    return _decode_token(token, TokenType.REFRESH)


# --- Symmetric encryption for secrets at rest --------------------------------
#
# Used for SmtpProfile.password_encrypted and CapturedCredential.field_value.
# Fernet's 32-byte key is internally split into a 128-bit HMAC-SHA256 signing
# key and a 128-bit AES-CBC encryption key - i.e. it is AES-128-CBC with a
# SHA-256 MAC, not literally "AES-256" of the payload, despite the key
# material being 256 bits total. It's still a solid authenticated-encryption
# choice (tamper-evident, includes a timestamp/nonce) - flagging the
# terminology only so it isn't a surprise in a compliance/audit context that
# specifically requires AES-256.
_fernet = Fernet(settings.ENCRYPTION_KEY.encode("utf-8"))


def encrypt_secret(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Ciphertext is invalid or was encrypted with a different key") from exc
