from pydantic import BaseModel, Field


class SettingsOut(BaseModel):
    retention_days: int


class SettingsUpdate(BaseModel):
    retention_days: int = Field(ge=1, le=3650)


class PurgeResult(BaseModel):
    purged_campaigns: int
