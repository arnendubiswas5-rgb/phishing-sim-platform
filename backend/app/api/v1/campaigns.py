import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.campaign import Campaign, CampaignStatus, CampaignTarget
from app.models.group import TargetGroup
from app.models.page import Page
from app.models.smtp_profile import SmtpProfile
from app.models.target import Target
from app.models.template import Template
from app.models.training import TrainingModule
from app.models.user import User, UserRole
from app.schemas.campaign import CampaignCreate, CampaignOut
from app.utils.tracking import generate_tracking_signature, generate_tracking_uuid
from app.workers.email_worker import dispatch_campaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# Campaigns send real email to real people and can be launched/paused - gate
# every mutation to admins/managers, same as the SMTP profile endpoints.
_MUTATE_ROLES = (UserRole.ADMIN, UserRole.MANAGER)


async def _get_campaign_or_404(db: AsyncSession, tenant_id: uuid.UUID, campaign_id: uuid.UUID) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None or campaign.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    # Listing is read-only, so viewers can see it too.
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.tenant_id == current_user.tenant_id)
        .order_by(Campaign.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_campaign_or_404(db, current_user.tenant_id, campaign_id)


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_MUTATE_ROLES)),
):
    template = await db.get(Template, payload.template_id)
    if template is None or template.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    page = await db.get(Page, payload.page_id)
    if page is None or page.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")

    smtp_profile = await db.get(SmtpProfile, payload.smtp_id)
    if smtp_profile is None or smtp_profile.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMTP profile not found")

    if payload.training_module_id is not None:
        module = await db.get(TrainingModule, payload.training_module_id)
        if module is None or module.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training module not found")

    # Re-scope target_ids to this tenant and to active targets only - a target_id
    # from another tenant, or one marked inactive, is silently dropped rather
    # than trusted, since target_ids arrives as free-form client input.
    unique_target_ids = set(payload.target_ids)
    result = await db.execute(
        select(Target.id)
        .join(TargetGroup, Target.group_id == TargetGroup.id)
        .where(
            TargetGroup.tenant_id == current_user.tenant_id,
            Target.id.in_(unique_target_ids),
            Target.is_active.is_(True),
        )
    )
    valid_target_ids = set(result.scalars().all())
    if not valid_target_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="None of the provided target_ids are valid, active targets belonging to your organization",
        )

    campaign = Campaign(
        tenant_id=current_user.tenant_id,
        name=payload.name,
        template_id=payload.template_id,
        page_id=payload.page_id,
        smtp_profile_id=payload.smtp_id,
        training_module_id=payload.training_module_id,
        campaign_type=payload.campaign_type,
        created_by=current_user.id,
    )
    for target_id in valid_target_ids:
        tracking_uuid = generate_tracking_uuid()
        campaign.recipients.append(
            CampaignTarget(
                target_id=target_id,
                tracking_uuid=tracking_uuid,
                tracking_sig=generate_tracking_signature(tracking_uuid),
            )
        )

    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/launch", response_model=CampaignOut)
async def launch_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_MUTATE_ROLES)),
):
    campaign = await _get_campaign_or_404(db, current_user.tenant_id, campaign_id)
    # DRAFT -> RUNNING starts a new campaign; PAUSED -> RUNNING resumes one -
    # /launch doubles as "resume" since /pause has no separate resume endpoint.
    if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.PAUSED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot launch a campaign in '{campaign.status.value}' status",
        )
    campaign.status = CampaignStatus.RUNNING
    await db.commit()
    await db.refresh(campaign)
    dispatch_campaign.delay(str(campaign.id))
    return campaign


@router.post("/{campaign_id}/pause", response_model=CampaignOut)
async def pause_campaign(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_MUTATE_ROLES)),
):
    campaign = await _get_campaign_or_404(db, current_user.tenant_id, campaign_id)
    if campaign.status != CampaignStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot pause a campaign in '{campaign.status.value}' status",
        )
    campaign.status = CampaignStatus.PAUSED
    await db.commit()
    await db.refresh(campaign)
    return campaign
