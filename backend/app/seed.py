import logging

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.user import User, UserRole
from app.utils.security import hash_password

logger = logging.getLogger(__name__)

DEFAULT_TENANT_NAME = "Default"
DEFAULT_TENANT_SLUG = "default"
DEFAULT_ADMIN_EMAIL = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin_ChangeMe_123!"


async def seed_default_admin() -> None:
    """Creates a default tenant + admin user the first time the app starts
    against an empty database, so there's always a way in.

    This account's credentials are public (they're in this source file) -
    change its password immediately in any environment beyond local dev.
    """
    async with AsyncSessionLocal() as db:
        has_any_user = (await db.execute(select(User.id).limit(1))).first() is not None
        if has_any_user:
            return

        tenant = (
            await db.execute(select(Tenant).where(Tenant.slug == DEFAULT_TENANT_SLUG))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(name=DEFAULT_TENANT_NAME, slug=DEFAULT_TENANT_SLUG)
            db.add(tenant)
            await db.flush()

        admin = User(
            tenant_id=tenant.id,
            email=DEFAULT_ADMIN_EMAIL,
            hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
            full_name="Default Admin",
            role=UserRole.ADMIN,
        )
        db.add(admin)
        await db.commit()
        logger.warning(
            "Seeded default admin user (email=%s). Log in and change this password immediately.",
            DEFAULT_ADMIN_EMAIL,
        )
