import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.campaign import Campaign, CampaignTarget, TrackingEvent, TrackingEventType
from app.models.target import Target
from app.models.user import User
from app.schemas.report import (
    CampaignReportOut,
    DepartmentBreakdown,
    TimelinePoint,
)

router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_campaign_or_404(db: AsyncSession, campaign_id: uuid.UUID, tenant_id: uuid.UUID) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None or campaign.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


def _distinct_targets_for(event_type: TrackingEventType):
    """COUNT(DISTINCT campaign_target_id) among rows matching event_type.

    CASE...END evaluates to NULL for non-matching rows, and COUNT(DISTINCT x)
    ignores NULLs by definition, so this counts each target at most once per
    event type even if they triggered it multiple times (e.g. a mail client
    re-fetching the open pixel, or a target retrying a login submission).
    """
    return func.count(func.distinct(case((TrackingEvent.event_type == event_type, TrackingEvent.campaign_target_id))))


@router.get("/campaign/{campaign_id}", response_model=CampaignReportOut)
async def campaign_report(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    # Reporting is read-only, so viewers (not just admins/managers) can see it.
    current_user: User = Depends(get_current_user),
):
    await _get_campaign_or_404(db, campaign_id, current_user.tenant_id)

    total_targets = await db.scalar(
        select(func.count()).select_from(CampaignTarget).where(CampaignTarget.campaign_id == campaign_id)
    )

    metrics = (
        await db.execute(
            select(
                _distinct_targets_for(TrackingEventType.SENT).label("emails_sent"),
                _distinct_targets_for(TrackingEventType.OPENED).label("unique_opens"),
                _distinct_targets_for(TrackingEventType.CLICKED).label("unique_clicks"),
                _distinct_targets_for(TrackingEventType.SUBMITTED).label("unique_submissions"),
            )
            .select_from(TrackingEvent)
            .join(CampaignTarget, TrackingEvent.campaign_target_id == CampaignTarget.id)
            .where(CampaignTarget.campaign_id == campaign_id)
        )
    ).one()

    report_rate = round((metrics.unique_submissions / total_targets) * 100, 2) if total_targets else 0.0

    return CampaignReportOut(
        campaign_id=campaign_id,
        total_targets=total_targets,
        emails_sent=metrics.emails_sent,
        unique_opens=metrics.unique_opens,
        unique_clicks=metrics.unique_clicks,
        unique_submissions=metrics.unique_submissions,
        report_rate=report_rate,
    )


@router.get("/campaign/{campaign_id}/timeline", response_model=list[TimelinePoint])
async def campaign_timeline(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_campaign_or_404(db, campaign_id, current_user.tenant_id)

    day = func.date(TrackingEvent.created_at).label("day")
    rows = (
        await db.execute(
            select(
                day,
                _distinct_targets_for(TrackingEventType.OPENED).label("opened"),
                _distinct_targets_for(TrackingEventType.CLICKED).label("clicked"),
                _distinct_targets_for(TrackingEventType.SUBMITTED).label("submitted"),
            )
            .select_from(TrackingEvent)
            .join(CampaignTarget, TrackingEvent.campaign_target_id == CampaignTarget.id)
            .where(CampaignTarget.campaign_id == campaign_id)
            .group_by(day)
            .order_by(day)
        )
    ).all()

    return [
        TimelinePoint(day=row.day, opened=row.opened, clicked=row.clicked, submitted=row.submitted)
        for row in rows
    ]


@router.get("/campaign/{campaign_id}/departments", response_model=list[DepartmentBreakdown])
async def campaign_departments(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_campaign_or_404(db, campaign_id, current_user.tenant_id)

    department = func.coalesce(Target.department, "Unknown").label("department")
    rows = (
        await db.execute(
            select(
                department,
                func.count(func.distinct(CampaignTarget.id)).label("total_targets"),
                _distinct_targets_for(TrackingEventType.OPENED).label("opened"),
                _distinct_targets_for(TrackingEventType.CLICKED).label("clicked"),
                _distinct_targets_for(TrackingEventType.SUBMITTED).label("submitted"),
            )
            .select_from(CampaignTarget)
            .join(Target, CampaignTarget.target_id == Target.id)
            # Left join so targets with no tracking events still contribute to
            # their department's total_targets (with zero interactions).
            .outerjoin(TrackingEvent, TrackingEvent.campaign_target_id == CampaignTarget.id)
            .where(CampaignTarget.campaign_id == campaign_id)
            .group_by(department)
            .order_by(department)
        )
    ).all()

    return [
        DepartmentBreakdown(
            department=row.department,
            total_targets=row.total_targets,
            opened=row.opened,
            clicked=row.clicked,
            submitted=row.submitted,
        )
        for row in rows
    ]
