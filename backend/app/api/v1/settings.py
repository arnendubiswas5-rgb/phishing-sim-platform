from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.schemas.settings import PurgeResult, SettingsOut, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    return SettingsOut(retention_days=tenant.retention_days)


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    tenant.retention_days = payload.retention_days
    await db.commit()
    return SettingsOut(retention_days=tenant.retention_days)


@router.post("/purge", response_model=PurgeResult)
async def purge_now(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    """Run the retention purge for this tenant immediately and return how many
    campaigns were removed. The same purge runs automatically each day via the
    Celery beat task; this is the admin's on-demand trigger."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    purged = await db.scalar(
        text("SELECT purge_expired_data(:tenant_id, :days)").bindparams(
            tenant_id=str(tenant.id), days=tenant.retention_days
        )
    )
    await db.commit()
    return PurgeResult(purged_campaigns=purged or 0)
