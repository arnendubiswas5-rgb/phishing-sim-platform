import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.page import Page, PageType
from app.models.user import User
from app.schemas.page import PageCreate, PageOut, PagePreviewOut, PageUpdate
from app.services.template_service import render_template_string

router = APIRouter(prefix="/pages", tags=["pages"])

# Dummy target data a page's Jinja variables are rendered with for preview.
# submit_url is deliberately a non-clickable placeholder, never a real link.
_PREVIEW_CONTEXT = {
    "first_name": "Alex",
    "last_name": "Doe",
    "email": "alex.doe@example.com",
    "submit_url": "#preview",
}


def _capture_for(page_type: PageType) -> bool:
    return page_type == PageType.CREDENTIAL


async def _get_owned_page(db: AsyncSession, page_id: uuid.UUID, user: User) -> Page:
    page = await db.get(Page, page_id)
    if page is None or page.tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return page


@router.post("", response_model=PageOut, status_code=status.HTTP_201_CREATED)
async def create_page(
    payload: PageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    page = Page(
        tenant_id=current_user.tenant_id,
        name=payload.name,
        page_type=payload.page_type,
        html_content=payload.html_content,
        logo_url=payload.logo_url,
        redirect_url=payload.redirect_url,
        capture_credentials=_capture_for(payload.page_type),
    )
    db.add(page)
    await db.commit()
    await db.refresh(page)
    return page


@router.get("", response_model=list[PageOut])
async def list_pages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Page)
        .where(Page.tenant_id == current_user.tenant_id)
        .order_by(Page.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{page_id}", response_model=PageOut)
async def get_page(
    page_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_page(db, page_id, current_user)


@router.put("/{page_id}", response_model=PageOut)
async def update_page(
    page_id: uuid.UUID,
    payload: PageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    page = await _get_owned_page(db, page_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(page, field, value)
    # Keep the capture flag consistent with the (possibly new) page type.
    if "page_type" in data:
        page.capture_credentials = _capture_for(page.page_type)
    await db.commit()
    await db.refresh(page)
    return page


@router.post("/{page_id}/preview", response_model=PagePreviewOut)
async def preview_page(
    page_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    page = await _get_owned_page(db, page_id, current_user)
    context = {**_PREVIEW_CONTEXT, "logo_url": page.logo_url or ""}
    return PagePreviewOut(html=render_template_string(page.html_content, context))
