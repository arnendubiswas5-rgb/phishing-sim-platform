import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus, CampaignType


class CampaignCreate(BaseModel):
    name: str
    template_id: uuid.UUID
    page_id: uuid.UUID
    smtp_id: uuid.UUID
    campaign_type: CampaignType
    training_module_id: uuid.UUID | None = None
    target_ids: list[uuid.UUID] = Field(min_length=1)


class CampaignOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    template_id: uuid.UUID
    page_id: uuid.UUID
    smtp_profile_id: uuid.UUID
    training_module_id: uuid.UUID | None
    campaign_type: CampaignType
    status: CampaignStatus
    launch_at: datetime | None
    created_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
