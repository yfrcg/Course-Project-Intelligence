from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceBundle:
    school_score: float = 0.0
    course_score: float = 0.0
    intent_score: float = 0.0
    keyword_score: float = 0.0

    platform_trust: float = 0.0
    domain_trust: float = 0.0
    content_richness: float = 0.0
    structure_quality: float = 0.0
    course_specificity: float = 0.0
    repo_health: float = 0.0
    reference_utility_score: float = 0.0
    freshness_score: float = 0.0
    popularity_score: float = 0.0

    penalty_score: float = 0.0
    cap: float = 1.0
    cap_reason: str | None = None

    school_match_strength: str = "none"
    school_group_match: str = "not_applicable"
    repo_type: str = "unknown"
    course_profile_id: str | None = None
    course_specific_assets: dict[str, bool] = field(default_factory=dict)
    course_negative_signals: list[str] = field(default_factory=list)
    positive_evidence: list[str] = field(default_factory=list)
    negative_evidence: list[str] = field(default_factory=list)
    reference_utility: list[str] = field(default_factory=list)


@dataclass
class ScoreBreakdown:
    relevance_score: float = 0.0
    source_value_score: float = 0.0
    freshness_popularity_score: float = 0.0
    raw_score: float = 0.0
    final_score: float = 0.0
    value_level: str = "low"
    confidence: str = "low"
    cap_reason: str | None = None


@dataclass
class ScoreExplanation:
    evidence_bundle: EvidenceBundle
    score_breakdown: ScoreBreakdown
    matched_school: str | None = None
    detected_school: str | None = None
    detected_school_id: str | None = None
    school_evidence: list[str] = field(default_factory=list)
    matched_school_aliases: list[str] = field(default_factory=list)
    matched_course: str | None = None
    matched_intent: str | None = None
    query_intent: str = "generic"
    candidate_intents: list[str] = field(default_factory=list)
    source_provider: str | None = None
    why_recommended: str = ""
    reasons: list[str] = field(default_factory=list)
    caveat: str = ""

    def __getattr__(self, name: str) -> Any:
        legacy_aliases = {
            "structure_score": "structure_quality",
            "negative_score": "penalty_score",
            "confidence_level": "confidence",
        }
        if name in legacy_aliases:
            return getattr(self, legacy_aliases[name])
        if hasattr(self.evidence_bundle, name):
            return getattr(self.evidence_bundle, name)
        if hasattr(self.score_breakdown, name):
            return getattr(self.score_breakdown, name)
        raise AttributeError(name)

    def as_dict(self) -> dict[str, Any]:
        evidence = asdict(self.evidence_bundle)
        breakdown = asdict(self.score_breakdown)
        flat = {
            **evidence,
            **breakdown,
            "structure_score": self.evidence_bundle.structure_quality,
            "negative_score": self.evidence_bundle.penalty_score,
            "confidence_level": self.score_breakdown.confidence,
            "matched_school": self.matched_school,
            "detected_school": self.detected_school,
            "detected_school_id": self.detected_school_id,
            "school_evidence": list(self.school_evidence),
            "matched_school_aliases": list(self.matched_school_aliases),
            "matched_course": self.matched_course,
            "matched_intent": self.matched_intent,
            "query_intent": self.query_intent,
            "candidate_intents": list(self.candidate_intents),
            "source_provider": self.source_provider,
            "why_recommended": self.why_recommended,
            "reasons": list(self.reasons),
            "positive_evidence": list(self.evidence_bundle.positive_evidence),
            "negative_evidence": list(self.evidence_bundle.negative_evidence),
            "reference_utility": list(self.evidence_bundle.reference_utility),
            "evidence_bundle": evidence,
            "score_breakdown": breakdown,
        }
        if self.caveat:
            flat["caveat"] = self.caveat
        return flat

    def summary(self) -> str:
        parts: list[str] = []
        if self.why_recommended:
            parts.append(self.why_recommended)
        if self.reasons:
            parts.append("; ".join(self.reasons[:5]))
        elif self.positive_evidence:
            parts.append("; ".join(self.positive_evidence[:5]))
        if self.cap_reason:
            parts.append(f"cap={self.cap_reason}")
        if self.negative_evidence:
            parts.append("; ".join(self.negative_evidence[:2]))
        return "; ".join(parts)
