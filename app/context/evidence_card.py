from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceCard(BaseModel):
    title: str = Field(..., description="Short source title or repository name.")
    url: str | None = Field(default=None, description="Source URL when available.")
    source_type: str = Field(default="unknown", description="Normalized source type for the evidence item.")
    relevance_reason: str = Field(..., description="Short explanation of why this item is relevant to the query.")
    usable_parts: list[str] = Field(default_factory=list, description="Short list of referenceable parts such as report, src, sql, or notes.")
    risk_flags: list[str] = Field(default_factory=list, description="Lightweight risk hints for agent-side safety handling.")
    recommended_usage: str = Field(..., description="Short usage guidance for the agent.")
    citation_hint: str | None = Field(default=None, description="Short source hint for downstream answers.")
    raw_score: float | None = Field(default=None, description="Original relevance score when available.")
