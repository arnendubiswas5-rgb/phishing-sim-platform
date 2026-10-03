from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.smtp_profile import SmtpProfile
from app.models.user import User, UserRole
from app.schemas.smtp import SmtpProfileCreate, SmtpProfileOut
from app.utils.security import encrypt_secret

router = APIRouter(prefix="/smtp", tags=["smtp"])


@router.post("", response_model=SmtpProfileOut, status_code=status.HTTP_201_CREATED)
async def create_smtp_profile(
    payload: SmtpProfileCreate,
    db: AsyncSession = Depends(get_db),
    # SMTP credentials are sensitive relay secrets - only admins/managers may add them.
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
):
    profile = SmtpProfile(
        tenant_id=current_user.tenant_id,
        name=payload.name,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password_encrypted=encrypt_secret(payload.password) if payload.password else None,
        use_tls=payload.use_tls,
        from_name=payload.from_name,
        from_email=payload.from_email,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("", response_model=list[SmtpProfileOut])
async def list_smtp_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(SmtpProfile).where(SmtpProfile.tenant_id == current_user.tenant_id))
    return result.scalars().all()
