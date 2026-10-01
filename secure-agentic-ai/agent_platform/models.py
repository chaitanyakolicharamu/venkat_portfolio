from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str = Field(min_length=3, max_length=1200)
    service: Literal["claims-api", "member-portal", "identity"] = "claims-api"
    user_id: Literal["demo-analyst", "demo-admin"] = "demo-analyst"


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool


class ToolResult(BaseModel):
    tool: str
    arguments: dict[str, Any]
    output: dict[str, Any]
    elapsed_ms: float
