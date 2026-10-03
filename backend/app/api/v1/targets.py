from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.group import TargetGroup
from app.models.target import Target
from app.models.user import User
from app.schemas.target import TargetGroupOut, TargetImportResult, TargetOut
from app.services.target_import_service import parse_target_csv

router = APIRouter(prefix="/targets", tags=["targets"])

DEFAULT_IMPORT_GROUP_NAME = "Imported Targets"
_MAX_IMPORT_BYTES = 5 * 1024 * 1024


@router.get("", response_model=list[TargetOut])
async def list_targets(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Target)
        .join(TargetGroup, Target.group_id == TargetGroup.id)
        .where(TargetGroup.tenant_id == current_user.tenant_id)
        .order_by(Target.created_at.desc())
        .offset(skip)
        .limit(min(limit, 500))
    )
    return result.scalars().all()


@router.get("/groups", response_model=list[TargetGroupOut])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(
            TargetGroup.id,
            TargetGroup.name,
            TargetGroup.description,
            TargetGroup.created_at,
            func.count(Target.id).label("target_count"),
        )
        .outerjoin(Target, Target.group_id == TargetGroup.id)
        .where(TargetGroup.tenant_id == current_user.tenant_id)
        .group_by(TargetGroup.id)
        .order_by(TargetGroup.created_at.desc())
    )
    return [
        TargetGroupOut(
            id=row.id,
            name=row.name,
            description=row.description,
            created_at=row.created_at,
            target_count=row.target_count,
        )
        for row in result.all()
    ]


@router.post("/import", response_model=TargetImportResult, status_code=status.HTTP_201_CREATED)
async def import_targets(
    file: UploadFile = File(...),
    group_name: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > _MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CSV file is too large",
        )

    rows, skipped_invalid = parse_target_csv(content)

    resolved_group_name = group_name or DEFAULT_IMPORT_GROUP_NAME
    group = (
        await db.execute(
            select(TargetGroup).where(
                TargetGroup.tenant_id == current_user.tenant_id,
                TargetGroup.name == resolved_group_name,
            )
        )
    ).scalar_one_or_none()
    if group is None:
        group = TargetGroup(tenant_id=current_user.tenant_id, name=resolved_group_name)
        db.add(group)
        await db.flush()

    inserted = 0
    if rows:
        stmt = (
            pg_insert(Target)
            .values([{**row, "group_id": group.id} for row in rows])
            .on_conflict_do_nothing(index_elements=["group_id", "email"])
            .returning(Target.id)
        )
        result = await db.execute(stmt)
        inserted = len(result.scalars().all())

    await db.commit()

    return TargetImportResult(
        group_id=group.id,
        group_name=group.name,
        inserted=inserted,
        skipped_duplicates=len(rows) - inserted,
        skipped_invalid=skipped_invalid,
    )
