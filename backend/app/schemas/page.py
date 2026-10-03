import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.page import PageType


class PageCreate(BaseModel):
    name: str
    page_type: PageType = PageType.CREDENTIAL
    html_content: str
    logo_url: str | None = None
    redirect_url: str | None = None


class PageUpdate(BaseModel):
    name: str | None = None
    page_type: PageType | None = None
    html_content: str | None = None
    logo_url: str | None = None
    redirect_url: str | None = None


class PageOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    page_type: PageType
    capture_credentials: bool
    redirect_url: str | None
    logo_url: str | None
    # Included so the admin list can render a preview thumbnail.
    html_content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PagePreviewOut(BaseModel):
    html: str
