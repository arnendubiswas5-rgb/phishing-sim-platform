import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TrainingModule(Base):
    """A piece of just-in-time security-awareness training shown to a target
    after they interact with a simulation. `quiz` is a JSON list of questions:
    [{"question": str, "options": [str, ...], "answer": <index int>}, ...]."""

    __tablename__ = "training_modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    quiz: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # Fraction of questions (0.0-1.0) a target must get right to pass.
    pass_threshold: Mapped[float] = mapped_column(default=0.7, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TrainingStatus(str, enum.Enum):
    ASSIGNED = "assigned"
    COMPLETED = "completed"


class TrainingAssignment(Base):
    """Links a target to a training module they were assigned, usually created
    automatically when the target submits credentials in a campaign. The
    assignment id is the public token in the /training/{id} URL."""

    __tablename__ = "training_assignments"
    __table_args__ = (
        # One assignment per (target, campaign) - a target who submits twice in
        # the same campaign isn't assigned the module twice.
        UniqueConstraint("campaign_id", "target_id", name="uq_training_assignment_campaign_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    training_module_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("training_modules.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("targets.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[TrainingStatus] = mapped_column(
        Enum(TrainingStatus), default=TrainingStatus.ASSIGNED, nullable=False
    )
    score: Mapped[float | None] = mapped_column(nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    module: Mapped["TrainingModule"] = relationship()
