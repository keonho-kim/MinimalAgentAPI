from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1)
    uuid: str = Field(min_length=1)
    message: str = Field(min_length=1)
    chat_history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    stream_id: str


class HitlEditedAction(BaseModel):
    name: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)


class HitlDecision(BaseModel):
    type: Literal["approve", "edit", "reject"]
    edited_action: HitlEditedAction | None = None
    message: str | None = None


class HitlResumeRequest(BaseModel):
    decisions: list[HitlDecision] = Field(min_length=1)
    approval_scope: Literal["once", "agent", "core"] = "once"


class HitlResumeResponse(BaseModel):
    stream_id: str
    status: str
