from typing import Any

from pydantic import BaseModel, Field


class AgentHypothesis(BaseModel):
    agent_id: str
    task_id: str
    conclusion: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence: dict[str, Any]
    assumptions: list[str] = Field(default_factory=list)


class ReasoningMeshResult(BaseModel):
    task_id: str
    verdict: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    hypotheses: list[AgentHypothesis]
    handoffs: list[dict[str, Any]]