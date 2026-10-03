import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.campaign import TrackingEventType


class SubmittedCredentials(BaseModel):
    """Data captured from a simulated credential-harvesting landing page.

    Never store real captured secrets in plaintext for real campaigns; this
    training platform should only be pointed at mock/decoy login forms.
    """

    fields: dict[str, str] = {}


class TrackingEventOut(BaseModel):
    id: uuid.UUID
    event_type: TrackingEventType
    created_at: datetime

    model_config = {"from_attributes": True}
