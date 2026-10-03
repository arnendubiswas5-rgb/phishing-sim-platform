import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ShortLink(Base):
    """Maps a short, innocuous-looking code to a CampaignTarget's tracking_uuid.

    Lets an email use {BASE_URL}/s/{code} instead of exposing the raw
    /t/{uuid}?sig=... tracker. GET /s/{code} recomputes the signature and
    302-redirects to the real tracking URL.
    """

    __tablename__ = "short_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    tracking_uuid: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_targets.tracking_uuid", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
