import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.short_link import ShortLink

# Unambiguous-ish alphanumeric alphabet for the 6-char code (62^6 ~ 56.8B).
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
_CODE_LEN = 6


def generate_short_code(length: int = _CODE_LEN) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


async def get_or_create_short_link(db: AsyncSession, tracking_uuid: uuid.UUID) -> str:
    """Returns the short code for a tracking_uuid, creating one if needed.

    Idempotent per tracking_uuid so re-sending a campaign reuses the same code.
    Retries on the (rare) code collision against the unique constraint.
    """
    existing = (
        await db.execute(select(ShortLink).where(ShortLink.tracking_uuid == tracking_uuid))
    ).scalar_one_or_none()
    if existing is not None:
        return existing.code

    for _ in range(10):
        code = generate_short_code()
        clash = (await db.execute(select(ShortLink.id).where(ShortLink.code == code))).first()
        if clash is None:
            db.add(ShortLink(code=code, tracking_uuid=tracking_uuid))
            await db.flush()
            return code
    raise RuntimeError("Could not allocate a unique short-link code after 10 attempts")
