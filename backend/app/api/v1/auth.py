import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AccessToken, RefreshTokenRequest, Token, UserOut
from app.utils.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Hashed once at import time so that logging in with an email nobody has still
# pays bcrypt's cost, instead of returning faster than a wrong-password
# attempt would and leaking which emails have accounts via response timing.
_DUMMY_PASSWORD_HASH = hash_password("not-a-real-password-used-only-for-timing")

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password",
    headers={"WWW-Authenticate": "Bearer"},
)

_INVALID_REFRESH_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired refresh token",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    matches = result.scalars().all()
    if len(matches) > 1:
        # email is only unique per-tenant, so the same address can exist under
        # more than one tenant. Login-by-email-alone can't safely pick one, so
        # refuse rather than guess which account to authenticate against.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is registered under multiple organizations; contact your administrator.",
        )
    user = matches[0] if matches else None

    if user is not None and user.is_active:
        password_ok = verify_password(form_data.password, user.hashed_password)
    else:
        verify_password(form_data.password, _DUMMY_PASSWORD_HASH)
        password_ok = False

    if user is None or not password_ok:
        raise _INVALID_CREDENTIALS

    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=AccessToken)
async def refresh(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = decode_refresh_token(payload.refresh_token)
        user_id = uuid.UUID(claims["sub"])
    except (TokenError, KeyError, ValueError):
        raise _INVALID_REFRESH_TOKEN

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise _INVALID_REFRESH_TOKEN

    return AccessToken(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
async def read_me(current_user: User = Depends(get_current_user)):
    return current_user
