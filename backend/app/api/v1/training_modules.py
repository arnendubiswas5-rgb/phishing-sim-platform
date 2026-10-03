import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.database import get_db
from app.models.training import TrainingModule
from app.models.user import User, UserRole
from app.schemas.training import TrainingModuleCreate, TrainingModuleOut, TrainingModuleUpdate

router = APIRouter(prefix="/training-modules", tags=["training"])

_MUTATE_ROLES = (UserRole.ADMIN, UserRole.MANAGER)


async def _get_or_404(db: AsyncSession, tenant_id: uuid.UUID, module_id: uuid.UUID) -> TrainingModule:
    module = await db.get(TrainingModule, module_id)
    if module is None or module.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training module not found")
    return module


@router.get("", response_model=list[TrainingModuleOut])
async def list_modules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TrainingModule)
        .where(TrainingModule.tenant_id == current_user.tenant_id)
        .order_by(TrainingModule.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{module_id}", response_model=TrainingModuleOut)
async def get_module(
    module_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_or_404(db, current_user.tenant_id, module_id)


@router.post("", response_model=TrainingModuleOut, status_code=status.HTTP_201_CREATED)
async def create_module(
    payload: TrainingModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_MUTATE_ROLES)),
):
    module = TrainingModule(
        tenant_id=current_user.tenant_id,
        name=payload.name,
        content=payload.content,
        quiz=[q.model_dump() for q in payload.quiz],
        pass_threshold=payload.pass_threshold,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return module


@router.put("/{module_id}", response_model=TrainingModuleOut)
async def update_module(
    module_id: uuid.UUID,
    payload: TrainingModuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_MUTATE_ROLES)),
):
    module = await _get_or_404(db, current_user.tenant_id, module_id)
    data = payload.model_dump(exclude_unset=True)
    if "quiz" in data and data["quiz"] is not None:
        data["quiz"] = [q if isinstance(q, dict) else q.model_dump() for q in payload.quiz]
    for key, value in data.items():
        setattr(module, key, value)
    await db.commit()
    await db.refresh(module)
    return module


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    module_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(*_MUTATE_ROLES)),
):
    module = await _get_or_404(db, current_user.tenant_id, module_id)
    await db.delete(module)
    await db.commit()
