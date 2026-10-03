from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import CampaignTarget, TrackingEvent, TrackingEventType

# CampaignTarget.status uses its own short vocabulary, independent of
# TrackingEventType's values (which log the more specific/verbose event kind -
# e.g. "email_sent"/"email_opened"/"link_clicked" vs status "sent"/"opened"/
# "clicked"). This maps one to the other and defines the forward-only order:
# a later event never gets overwritten by an earlier one arriving out of
# order (e.g. a mail client "opening" the message after the target already
# clicked through).
_EVENT_STATUS = {
    TrackingEventType.SENT: "sent",
    TrackingEventType.OPENED: "opened",
    TrackingEventType.CLICKED: "clicked",
    TrackingEventType.SUBMITTED: "submitted",
}
_STATUS_ORDER = ["pending", "sent", "opened", "clicked", "submitted"]


async def record_event(
    db: AsyncSession,
    campaign_target: CampaignTarget,
    event_type: TrackingEventType,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> TrackingEvent:
    event = TrackingEvent(
        campaign_target_id=campaign_target.id,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)

    new_status = _EVENT_STATUS[event_type]
    current_rank = _STATUS_ORDER.index(campaign_target.status) if campaign_target.status in _STATUS_ORDER else -1
    new_rank = _STATUS_ORDER.index(new_status)
    if new_rank > current_rank:
        campaign_target.status = new_status

    await db.commit()
    await db.refresh(event)
    return event
