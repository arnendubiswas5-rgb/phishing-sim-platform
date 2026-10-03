import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tenant(Base):
    """A customer organization. Every tenant-owned resource hangs off this via tenant_id
    so that queries can be scoped per-tenant and one customer's campaigns/targets/captured
    credentials are never reachable from another customer's session."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    # Days of campaign/tracking data kept before the daily purge job removes it.
    retention_days: Mapped[int] = mapped_column(Integer, default=90, server_default="90", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    target_groups: Mapped[list["TargetGroup"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    templates: Mapped[list["Template"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    pages: Mapped[list["Page"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    smtp_profiles: Mapped[list["SmtpProfile"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
