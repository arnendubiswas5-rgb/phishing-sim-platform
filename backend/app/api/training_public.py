"""Public, unauthenticated training pages.

Mounted at the app root (not under /api/v1) - the assignment id in the URL is
the capability: knowing it is what authorizes viewing/completing that one
assignment, the same trust model as the /t/ tracking links.
"""
import html
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.campaign import CampaignTarget, TrackingEvent, TrackingEventType
from app.models.training import TrainingAssignment, TrainingStatus

router = APIRouter(prefix="/training", tags=["training-public"])


async def _get_assignment(db: AsyncSession, assignment_id: uuid.UUID) -> TrainingAssignment | None:
    result = await db.execute(
        select(TrainingAssignment)
        .where(TrainingAssignment.id == assignment_id)
        # Eager-load the module: it's accessed while rendering, outside the
        # async-safe context a lazy load would need.
        .options(selectinload(TrainingAssignment.module))
    )
    return result.scalar_one_or_none()


def _render_page(assignment: TrainingAssignment, *, completed: bool, message: str | None = None) -> str:
    module = assignment.module
    quiz = module.quiz or []

    if completed:
        body = (
            '<div class="banner ok">You have completed this training. Thank you!</div>'
            f"<h1>{html.escape(module.name)}</h1>"
            f'<div class="content">{module.content}</div>'
        )
        return _PAGE.format(title=html.escape(module.name), body=body)

    questions_html = []
    for i, q in enumerate(quiz):
        options = "".join(
            f'<label class="opt"><input type="radio" name="q{i}" value="{j}" required> '
            f"{html.escape(str(opt))}</label>"
            for j, opt in enumerate(q.get("options", []))
        )
        questions_html.append(
            f'<fieldset><legend>{html.escape(str(q.get("question", "")))}</legend>{options}</fieldset>'
        )

    alert = f'<div class="banner err">{html.escape(message)}</div>' if message else ""
    quiz_html = (
        f'<form method="post" action="/training/{assignment.id}/submit">'
        + "".join(questions_html)
        + '<button type="submit">Submit answers</button></form>'
        if quiz
        else '<form method="post" action="/training/{0}/submit"><button type="submit">'
        "Mark as complete</button></form>".format(assignment.id)
    )

    body = (
        f"{alert}"
        f"<h1>{html.escape(module.name)}</h1>"
        f'<div class="content">{module.content}</div>'
        f"<h2>Quick quiz</h2>{quiz_html}"
    )
    return _PAGE.format(title=html.escape(module.name), body=body)


@router.get("/{assignment_id}", response_class=HTMLResponse)
async def training_page(assignment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    assignment = await _get_assignment(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return HTMLResponse(
        _render_page(assignment, completed=assignment.status == TrainingStatus.COMPLETED)
    )


@router.post("/{assignment_id}/submit")
async def training_submit(assignment_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    assignment = await _get_assignment(db, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if assignment.status == TrainingStatus.COMPLETED:
        return RedirectResponse(url=f"/training/{assignment_id}", status_code=status.HTTP_303_SEE_OTHER)

    quiz = assignment.module.quiz or []
    form = await request.form()

    # Grade: fraction of questions answered correctly.
    correct = 0
    for i, q in enumerate(quiz):
        raw = form.get(f"q{i}")
        try:
            if raw is not None and int(raw) == int(q.get("answer", -1)):
                correct += 1
        except (TypeError, ValueError):
            pass
    score = (correct / len(quiz)) if quiz else 1.0

    if score < assignment.module.pass_threshold:
        return HTMLResponse(
            _render_page(
                assignment,
                completed=False,
                message=f"You scored {round(score * 100)}%. Please review the material and try again.",
            )
        )

    assignment.status = TrainingStatus.COMPLETED
    assignment.score = score
    from datetime import datetime, timezone

    assignment.completed_at = datetime.now(timezone.utc)

    # Log a training_completed event against this target's campaign participation.
    campaign_target = (
        await db.execute(
            select(CampaignTarget).where(
                CampaignTarget.campaign_id == assignment.campaign_id,
                CampaignTarget.target_id == assignment.target_id,
            )
        )
    ).scalar_one_or_none()
    if campaign_target is not None:
        db.add(
            TrackingEvent(
                campaign_target_id=campaign_target.id,
                event_type=TrackingEventType.TRAINING_COMPLETED,
            )
        )

    await db.commit()
    await db.refresh(assignment)
    return HTMLResponse(_render_page(assignment, completed=True))


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 680px; margin: 40px auto;
          padding: 0 24px; color: #1a1a2e; line-height: 1.55; }}
  h1 {{ font-size: 1.6rem; }} h2 {{ font-size: 1.2rem; margin-top: 32px; }}
  .banner {{ border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; }}
  .banner.ok {{ background: #d3f9d8; border: 1px solid #8ce99a; }}
  .banner.err {{ background: #fff5f5; border: 1px solid #ffc9c9; }}
  fieldset {{ border: 1px solid #dee2e6; border-radius: 8px; margin: 16px 0; padding: 12px 16px; }}
  legend {{ font-weight: 600; padding: 0 6px; }}
  .opt {{ display: block; margin: 6px 0; }}
  button {{ margin-top: 20px; padding: 12px 24px; background: #2b59ff; color: #fff; border: 0;
            border-radius: 6px; font-weight: 600; font-size: 1rem; cursor: pointer; }}
  .content {{ background: #f8f9fa; border-radius: 8px; padding: 16px 20px; }}
</style></head><body>{body}</body></html>"""
