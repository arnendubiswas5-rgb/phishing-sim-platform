import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class TemplateCreate(BaseModel):
    name: str
    subject: str
    html_body: str
    text_body: str | None = None
    sender_name: str
    sender_email: EmailStr


class TemplateOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    subject: str
    html_body: str
    text_body: str | None
    sender_name: str
    sender_email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TemplatePreviewOut(BaseModel):
    subject: str
    html_body: str
    text_body: str | None
