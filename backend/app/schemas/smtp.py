import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class SmtpProfileCreate(BaseModel):
    name: str
    host: str
    port: int = 587
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    from_name: str
    from_email: EmailStr


class SmtpProfileOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    host: str
    port: int
    username: str | None
    use_tls: bool
    from_name: str
    from_email: str
    created_at: datetime

    # deliberately no password/password_encrypted field here - never returned via the API

    model_config = {"from_attributes": True}
