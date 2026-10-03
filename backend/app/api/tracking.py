from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.campaign import CampaignTarget, CapturedCredential, TrackingEventType
from app.models.page import Page
from app.models.template import Template
from app.models.training import TrainingAssignment
from app.services.template_service import render_template_string
from app.services.tracking_service import record_event
from app.utils.ratelimit import rate_limit_tracking
from app.utils.security import encrypt_secret
from app.utils.tracking import verify_tracking_signature

# Rate-limit every tracking endpoint per client IP (see app.utils.ratelimit) to
# blunt enumeration of tracking UUIDs/signatures.
router = APIRouter(prefix="/t", tags=["tracking"], dependencies=[Depends(rate_limit_tracking)])

# 1x1 transparent GIF89a (verified with Pillow: size (1,1), transparency
# present), embedded as the open-tracking beacon in every campaign email.
_PIXEL_GIF = bytes.fromhex(
    "4749463839610100010080000000000000ffffff21f90401000000002c00000000010001000002024401003b"
)

_NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
}

_EDUCATION_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>This was a phishing simulation</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 640px; margin: 48px auto;
           padding: 0 24px; color: #1a1a2e; line-height: 1.5; }
    h1 { font-size: 1.5rem; }
    .banner { background: #fff3cd; border: 1px solid #ffe69c; border-radius: 8px; padding: 16px 20px; margin-bottom: 24px; }
    .flag { border-left: 4px solid #d9480f; background: #fff5f5; padding: 12px 16px; margin: 12px 0; border-radius: 4px; }
    .flag h3 { margin: 0 0 4px 0; font-size: 1rem; }
    code { background: #f1f3f5; padding: 2px 6px; border-radius: 4px; }
    .cta { display: inline-block; margin-top: 24px; padding: 12px 24px; background: #2b59ff; color: white;
           text-decoration: none; border-radius: 6px; font-weight: 600; }
  </style>
</head>
<body>
  <div class="banner"><strong>Hi {{ first_name }},</strong> this was a simulated phishing exercise run by your
    organization's security team - no real data was compromised.</div>

  <h1>How to spot this next time</h1>

  <div class="flag">
    <h3>1. Sender domain</h3>
    <p>This message claimed to be from <code>{{ sender_email }}</code>. Always check whether the domain
    after the <code>@</code> (<code>{{ sender_domain }}</code>) actually matches your organization's real
    domain, not just the display name.</p>
  </div>

  <div class="flag">
    <h3>2. URL mismatch</h3>
    <p>The link you clicked led to <code>{{ destination_domain }}</code> - not your organization's real
    website. Before clicking, hover over links to preview their actual destination in your browser or mail
    client's status bar.</p>
  </div>

  <div class="flag">
    <h3>3. Urgency</h3>
    <p>Phishing emails often pressure you to act immediately ("your account will be locked", "action
    required within 24 hours") to stop you from pausing and verifying. If a message creates a sense of
    urgency, that's itself a reason to slow down and confirm through a separate, trusted channel.</p>
  </div>

  <a class="cta" href="#" onclick="return false;">Start 2-minute training module</a>
</body>
</html>
"""

def _client_ip(request: Request) -> str | None:
    # Trust X-Real-IP (our own nginx sets it to $remote_addr, which a client
    # cannot forge) over X-Forwarded-For, whose leftmost hop a client can
    # freely spoof when there's exactly one trusted proxy in front of us.
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else None


async def _get_campaign_target(db: AsyncSession, tracking_uuid: UUID) -> CampaignTarget | None:
    result = await db.execute(
        select(CampaignTarget)
        .where(CampaignTarget.tracking_uuid == tracking_uuid)
        .options(selectinload(CampaignTarget.campaign), selectinload(CampaignTarget.target))
    )
    return result.scalar_one_or_none()


@router.get("/{uuid}/pixel.gif")
async def track_pixel(uuid: UUID, request: Request, db: AsyncSession = Depends(get_db)):
    campaign_target = await _get_campaign_target(db, uuid)
    if campaign_target is not None:
        await record_event(
            db,
            campaign_target,
            TrackingEventType.OPENED,
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    # Always return the pixel, even for an unknown uuid - a distinguishable
    # response here would let someone probe which tracking links are real.
    return Response(content=_PIXEL_GIF, media_type="image/gif", headers=_NO_CACHE_HEADERS)


@router.get("/{uuid}")
async def track_click(uuid: UUID, sig: str, request: Request, db: AsyncSession = Depends(get_db)):
    if not verify_tracking_signature(uuid, sig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    campaign_target = await _get_campaign_target(db, uuid)
    if campaign_target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    await record_event(
        db,
        campaign_target,
        TrackingEventType.CLICKED,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    page = await db.get(Page, campaign_target.campaign.page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if page.capture_credentials:
        # The page's own form needs to know where to POST to - make that (and
        # basic personalization) available as Jinja variables in html_content,
        # e.g. <form method="post" action="{{ submit_url }}">.
        target = campaign_target.target
        context = {
            "first_name": target.first_name or "",
            "last_name": target.last_name or "",
            "email": target.email,
            "submit_url": f"{settings.APP_BASE_URL}/t/{uuid}/submit?sig={sig}",
            "logo_url": page.logo_url or "",
        }
        return HTMLResponse(content=render_template_string(page.html_content, context))

    if not page.redirect_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Landing page is misconfigured (no redirect_url set)",
        )
    return RedirectResponse(url=page.redirect_url)


@router.post("/{uuid}/submit")
async def track_submit(
    uuid: UUID,
    sig: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    username: str | None = Form(default=None),
    password: str | None = Form(default=None),
):
    # Not explicitly required by the spec for this endpoint, but the whole
    # point of tracking_sig is to keep every state-changing tracking action
    # gated on it, and this endpoint accepts and stores actual credentials -
    # the most sensitive action in the whole flow.
    if not verify_tracking_signature(uuid, sig):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    campaign_target = await _get_campaign_target(db, uuid)
    if campaign_target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    event = await record_event(
        db,
        campaign_target,
        TrackingEventType.SUBMITTED,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    submitted_fields = {"username": username, "password": password}
    for field_name, field_value in submitted_fields.items():
        if field_value:
            db.add(
                CapturedCredential(
                    tracking_event_id=event.id,
                    field_name=field_name,
                    field_value=encrypt_secret(field_value),
                )
            )

    # Assign the campaign's training module (if any) to this target. Idempotent:
    # the (campaign_id, target_id) unique constraint means resubmitting doesn't
    # create a second assignment.
    campaign = campaign_target.campaign
    if campaign.training_module_id is not None:
        existing = (
            await db.execute(
                select(TrainingAssignment).where(
                    TrainingAssignment.campaign_id == campaign.id,
                    TrainingAssignment.target_id == campaign_target.target_id,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                TrainingAssignment(
                    tenant_id=campaign.tenant_id,
                    training_module_id=campaign.training_module_id,
                    campaign_id=campaign.id,
                    target_id=campaign_target.target_id,
                )
            )

    await db.commit()

    # 303, not the RedirectResponse default of 307: this follows a POST and
    # must switch the browser to GET for the next request (Post/Redirect/Get),
    # or it would re-submit the captured form data to /education.
    return RedirectResponse(url=f"/t/{uuid}/education", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{uuid}/education", response_class=HTMLResponse)
async def track_education(uuid: UUID, db: AsyncSession = Depends(get_db)):
    campaign_target = await _get_campaign_target(db, uuid)
    if campaign_target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    template = await db.get(Template, campaign_target.campaign.template_id)
    sender_email = template.sender_email if template is not None else "unknown@example.com"
    sender_domain = sender_email.rsplit("@", 1)[-1]
    destination_domain = urlparse(settings.APP_BASE_URL).netloc or settings.APP_BASE_URL

    context = {
        "first_name": campaign_target.target.first_name or "there",
        "sender_email": sender_email,
        "sender_domain": sender_domain,
        "destination_domain": destination_domain,
    }
    return HTMLResponse(content=render_template_string(_EDUCATION_TEMPLATE, context))
