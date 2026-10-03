import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PageType(str, enum.Enum):
    """What a landing page is for. Drives tracking behavior: CREDENTIAL renders
    the page's form so submissions are captured; REDIRECT sends the target on to
    redirect_url; EDUCATION shows awareness content with nothing to submit."""

    CREDENTIAL = "credential"
    EDUCATION = "education"
    REDIRECT = "redirect"


class Page(Base):
    """A landing page a campaign's tracking link sends the target to. If
    capture_credentials is set, the page's form posts to the tracking/submit
    endpoint instead of a real destination."""

    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    page_type: Mapped[PageType] = mapped_column(
        Enum(PageType, name="pagetype"), default=PageType.CREDENTIAL, nullable=False
    )
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    # Kept in sync with page_type on write (True only for CREDENTIAL); the
    # tracking endpoint keys its form-vs-redirect behavior off this flag.
    capture_credentials: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    redirect_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Optional logo shown on the landing page, exposed to the page's HTML as the
    # Jinja variable {{ logo_url }}.
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship(back_populates="pages")
