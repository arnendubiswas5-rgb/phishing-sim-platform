from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.short_link import ShortLink
from app.utils.ratelimit import rate_limit_tracking
from app.utils.tracking import generate_tracking_signature

# Public, short, innocuous-looking redirector. Rate-limited like /t to blunt
# enumeration of codes.
router = APIRouter(prefix="/s", tags=["short-links"], dependencies=[Depends(rate_limit_tracking)])


@router.get("/{code}")
async def resolve_short_link(code: str, db: AsyncSession = Depends(get_db)):
    short_link = (
        await db.execute(select(ShortLink).where(ShortLink.code == code))
    ).scalar_one_or_none()
    if short_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Recompute the signature rather than storing it, so the real tracker URL is
    # only ever materialized at redirect time.
    sig = generate_tracking_signature(short_link.tracking_uuid)
    return RedirectResponse(
        url=f"/t/{short_link.tracking_uuid}?sig={sig}",
        status_code=status.HTTP_302_FOUND,
    )
