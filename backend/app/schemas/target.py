import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class TargetOut(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    email: EmailStr
    first_name: str | None
    last_name: str | None
    department: str | None
    position: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TargetGroupOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    target_count: int


class TargetImportResult(BaseModel):
    group_id: uuid.UUID
    group_name: str
    inserted: int
    skipped_duplicates: int
    skipped_invalid: int
