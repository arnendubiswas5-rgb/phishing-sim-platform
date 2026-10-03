import asyncio
import logging
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage

import aiosmtplib
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.config import settings
from app.models.campaign import Campaign, CampaignTarget, TrackingEvent, TrackingEventType
from app.models.smtp_profile import SmtpProfile
from app.models.template import Template
from app.models.tenant import Tenant
from app.services.short_link_service import get_or_create_short_link
from app.services.template_service import render_template_string
from app.utils.security import decrypt_secret

logger = logging.getLogger(__name__)

celery_app = Celery("phishing_sim", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

# Run the retention purge once a day at 03:00. Requires `celery beat` to be
# running alongside the worker (e.g. `celery -A app.workers.email_worker.celery_app beat`).
celery_app.conf.beat_schedule = {
    "daily-purge-expired-data": {
        "task": "workers.purge_expired_data",
        "schedule": crontab(hour=3, minute=0),
    }
}

# A dedicated engine for this worker process, separate from the one FastAPI
# uses. Each task invocation runs its async work inside its own asyncio.run()
# event loop (Celery tasks are plain sync callables); pooled asyncpg
# connections created under one event loop are not valid on the next one, so
# this engine uses NullPool (no cross-invocation connection reuse) rather than
# risking "attached to a different loop" errors on the second task a worker
# process handles.
_worker_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
_WorkerSessionLocal = async_sessionmaker(bind=_worker_engine, expire_on_commit=False, class_=AsyncSession)


@celery_app.task(name="workers.dispatch_campaign", bind=True, max_retries=3, default_retry_delay=60)
def dispatch_campaign(self, campaign_id: str) -> dict:
    try:
        return asyncio.run(_dispatch_campaign_async(campaign_id))
    except Exception as exc:
        raise self.retry(exc=exc)


@celery_app.task(name="workers.purge_expired_data")
def purge_expired_data() -> dict:
    """Daily retention job: for each tenant, delete campaign data older than that
    tenant's retention_days via the purge_expired_data() Postgres function."""
    return asyncio.run(_purge_expired_data_async())


async def _purge_expired_data_async() -> dict:
    async with _WorkerSessionLocal() as db:
        tenants = (await db.execute(select(Tenant))).scalars().all()
        total_purged = 0
        for tenant in tenants:
            purged = await db.scalar(
                text("SELECT purge_expired_data(:tenant_id, :days)").bindparams(
                    tenant_id=str(tenant.id), days=tenant.retention_days
                )
            )
            total_purged += purged or 0
        await db.commit()
        logger.info("purge_expired_data: removed %s campaigns across %s tenants", total_purged, len(tenants))
        return {"purged_campaigns": total_purged, "tenants": len(tenants)}


async def _dispatch_campaign_async(campaign_id: str) -> dict:
    async with _WorkerSessionLocal() as db:
        campaign = await db.get(Campaign, uuid.UUID(campaign_id))
        if campaign is None:
            logger.warning("dispatch_campaign: campaign %s not found", campaign_id)
            return {"sent": 0, "failed": 0, "total": 0}

        template = await db.get(Template, campaign.template_id)
        smtp_profile = await db.get(SmtpProfile, campaign.smtp_profile_id)

        # Only targets still 'pending' - this is what makes a retried/re-run
        # dispatch safe: anyone already marked 'sent' by a prior attempt is
        # skipped instead of being emailed a second time.
        result = await db.execute(
            select(CampaignTarget)
            .where(CampaignTarget.campaign_id == campaign.id, CampaignTarget.status == "pending")
            .options(selectinload(CampaignTarget.target))
        )
        campaign_targets = result.scalars().all()

        sent = 0
        failed = 0
        for campaign_target in campaign_targets:
            try:
                await _send_one(db, template, smtp_profile, campaign_target)
                sent += 1
            except Exception:
                # One bad address/refused recipient shouldn't abort delivery to
                # everyone else in the campaign - log and move on. The target
                # stays 'pending', so a later dispatch_campaign run will retry it.
                logger.exception(
                    "dispatch_campaign: failed to send to campaign_target %s", campaign_target.id
                )
                failed += 1

        return {"sent": sent, "failed": failed, "total": len(campaign_targets)}


async def _send_one(
    db: AsyncSession,
    template: Template,
    smtp_profile: SmtpProfile,
    campaign_target: CampaignTarget,
) -> None:
    # Innocuous-looking short link ({BASE_URL}/s/{code}) that redirects to the
    # raw tracker; templates can use {{ short_url }} instead of {{ tracking_url }}.
    short_code = await get_or_create_short_link(db, campaign_target.tracking_uuid)

    context = {
        "first_name": campaign_target.target.first_name or "",
        "last_name": campaign_target.target.last_name or "",
        "email": campaign_target.target.email,
        "department": campaign_target.target.department or "",
        "position": campaign_target.target.position or "",
        "tracking_url": f"{settings.APP_BASE_URL}/t/{campaign_target.tracking_uuid}?sig={campaign_target.tracking_sig}",
        "short_url": f"{settings.APP_BASE_URL}/s/{short_code}",
        "tracking_pixel": f"{settings.APP_BASE_URL}/t/{campaign_target.tracking_uuid}/pixel.gif",
    }

    message = EmailMessage()
    message["Subject"] = render_template_string(template.subject, context)
    # The visible From: header uses the template's pretext sender identity
    # (what the target sees); the SMTP envelope sender below uses the relay's
    # own authorized address, which many relays require to match a verified
    # domain regardless of what the message headers claim.
    message["From"] = f"{template.sender_name} <{template.sender_email}>"
    message["To"] = campaign_target.target.email

    html_body = render_template_string(template.html_body, context)
    if template.text_body:
        message.set_content(render_template_string(template.text_body, context))
        message.add_alternative(html_body, subtype="html")
    else:
        message.set_content(html_body, subtype="html")

    # TLS mode depends on the port:
    #   465 -> implicit TLS (connection is encrypted from the start)
    #   587 (or any other) with use_tls set -> STARTTLS (upgrade after connect)
    #   use_tls off (e.g. a local Mailpit catcher on 1025) -> plaintext
    # aiosmtplib rejects use_tls and start_tls both being True, so they're
    # mutually exclusive here.
    implicit_tls = smtp_profile.port == 465
    await aiosmtplib.send(
        message,
        sender=smtp_profile.from_email,
        recipients=[campaign_target.target.email],
        hostname=smtp_profile.host,
        port=smtp_profile.port,
        username=smtp_profile.username or None,
        password=decrypt_secret(smtp_profile.password_encrypted) if smtp_profile.password_encrypted else None,
        use_tls=implicit_tls,
        start_tls=smtp_profile.use_tls and not implicit_tls,
        timeout=30,
    )

    campaign_target.status = "sent"
    campaign_target.sent_at = datetime.now(timezone.utc)
    db.add(TrackingEvent(campaign_target_id=campaign_target.id, event_type=TrackingEventType.SENT))
    await db.commit()
