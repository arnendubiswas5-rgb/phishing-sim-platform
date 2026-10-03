import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.template import Template
from app.models.user import User
from app.schemas.template import TemplateCreate, TemplateOut, TemplatePreviewOut
from app.services.template_service import render_preview

router = APIRouter(prefix="/templates", tags=["templates"])


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = Template(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("", response_model=list[TemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Template).where(Template.tenant_id == current_user.tenant_id))
    return result.scalars().all()


@router.post("/{template_id}/preview", response_model=TemplatePreviewOut)
async def preview_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = await db.get(Template, template_id)
    if template is None or template.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    return TemplatePreviewOut(
        subject=render_preview(template.subject),
        html_body=render_preview(template.html_body),
        text_body=render_preview(template.text_body) if template.text_body else None,
    )
