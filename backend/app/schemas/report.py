import uuid
from datetime import date

from pydantic import BaseModel


class CampaignReportOut(BaseModel):
    campaign_id: uuid.UUID
    total_targets: int
    emails_sent: int
    unique_opens: int
    unique_clicks: int
    unique_submissions: int
    # unique_submissions / total_targets * 100 - the standard headline metric:
    # what fraction of targets ultimately entered fake credentials.
    report_rate: float


class TimelinePoint(BaseModel):
    """One day's distinct-target counts for each tracked interaction, for the
    campaign trend line chart."""

    day: date
    opened: int
    clicked: int
    submitted: int


class DepartmentBreakdown(BaseModel):
    department: str
    total_targets: int
    opened: int
    clicked: int
    submitted: int
