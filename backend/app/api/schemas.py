"""Pydantic request/response models for the REST API. Distinct from the
LLM structured-output schemas in app.models.schemas."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.config import settings


class StartDebateRequest(BaseModel):
    decision_question: str
    options: list[str] = Field(min_length=2)
    context: str = ""
    min_rounds: int = settings.min_rounds
    max_rounds: int = settings.max_rounds


class StartDebateResponse(BaseModel):
    thread_id: str


class ResumeRequest(BaseModel):
    action: Literal["approve", "edit", "reopen"]
    payload: Optional[dict] = None
