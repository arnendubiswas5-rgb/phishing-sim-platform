import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignType(str, enum.Enum):
    """Categorizes what a campaign is measuring, for reporting purposes - actual
    runtime behavior (whether the landing page captures credentials, etc.) is
    still driven entirely by the Page/Template it references."""

    CREDENTIAL_HARVEST = "credential_harvest"
    LINK_CLICK = "link_click"
    ATTACHMENT = "attachment"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("templates.id"), nullable=False)
    page_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pages.id"), nullable=False)
    smtp_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smtp_profiles.id"), nullable=False)
    # Optional training assigned to targets who fall for this campaign.
    training_module_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("training_modules.id", ondelete="SET NULL"), nullable=True
    )
    campaign_type: Mapped[CampaignType] = mapped_column(Enum(CampaignType), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False)
    launch_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="campaigns")
    template: Mapped["Template"] = relationship()
    page: Mapped["Page"] = relationship()
    smtp_profile: Mapped["SmtpProfile"] = relationship()
    created_by_user: Mapped["User"] = relationship()
    recipients: Mapped[list["CampaignTarget"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignTarget(Base):
    """A single target's participation in a campaign.

    tracking_uuid is the public identifier embedded in tracking URLs. tracking_sig
    is an HMAC computed over (tracking_uuid, campaign_id, target_id) with a
    server-side secret, so a tracking link's signature can be verified before any
    database lookup happens - this stops link enumeration/tampering from turning
    into a way to probe or forge other targets' tracking events.
    """

    __tablename__ = "campaign_targets"
    __table_args__ = (UniqueConstraint("campaign_id", "target_id", name="uq_campaign_targets_campaign_target"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("targets.id", ondelete="CASCADE"), nullable=False)
    tracking_uuid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, index=True, default=uuid.uuid4, nullable=False
    )
    tracking_sig: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    campaign: Mapped["Campaign"] = relationship(back_populates="recipients")
    target: Mapped["Target"] = relationship()
    events: Mapped[list["TrackingEvent"]] = relationship(back_populates="campaign_target", cascade="all, delete-orphan")


class TrackingEventType(str, enum.Enum):
    # Value is "email_sent" (not "sent") deliberately - CampaignTarget.status
    # uses the literal string "sent" for that same moment, and the two
    # vocabularies are intentionally independent (event log vs. status field).
    SENT = "email_sent"
    OPENED = "email_opened"
    CLICKED = "link_clicked"
    SUBMITTED = "data_submitted"
    # Positive outcome: the target completed the assigned awareness training.
    # Not part of the sent->opened->clicked->submitted progression, so it is
    # logged directly rather than via tracking_service.record_event().
    TRAINING_COMPLETED = "training_completed"


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_target_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_targets.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[TrackingEventType] = mapped_column(Enum(TrackingEventType), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign_target: Mapped["CampaignTarget"] = relationship(back_populates="events")
    captured_credentials: Mapped[list["CapturedCredential"]] = relationship(
        back_populates="tracking_event", cascade="all, delete-orphan"
    )


class CapturedCredential(Base):
    """One form field captured from a SUBMITTED tracking event's landing page.

    field_value holds whatever the target typed - which, on a real engagement, may
    be their actual password. Treat this table as highly sensitive: encrypt at
    rest, restrict access to it separately from general campaign reporting, and
    purge it on a retention schedule agreed with the engagement's stakeholders.
    """

    __tablename__ = "captured_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tracking_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tracking_events.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tracking_event: Mapped["TrackingEvent"] = relationship(back_populates="captured_credentials")
