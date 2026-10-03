import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    # Index into `options` of the correct answer.
    answer: int = Field(ge=0)


class TrainingModuleCreate(BaseModel):
    name: str
    content: str
    quiz: list[QuizQuestion] = Field(default_factory=list)
    pass_threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class TrainingModuleUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    quiz: list[QuizQuestion] | None = None
    pass_threshold: float | None = Field(default=None, ge=0.0, le=1.0)


class TrainingModuleOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    content: str
    quiz: list[QuizQuestion]
    pass_threshold: float
    created_at: datetime

    model_config = {"from_attributes": True}
