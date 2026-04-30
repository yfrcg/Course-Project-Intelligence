from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import SearchResultItem
from app.utils.github_urls import is_github_repo_url
from app.utils.text import unique_preserve_order


COPY_RISK_TERMS = [
    "homework",
    "assignment",
    "lab",
    "report",
    "course design",
    "project",
    "src",
    "code",
    "作业",
    "实验",
    "报告",
    "课程设计",
    "源码",
]

BROAD_QUERY_TERMS = [
    "database project",
    "course materials",
    "cs course resources",
    "大学课程资料",
    "课程设计参考",
    "学习资料",
    "公开资料",
    "课程资料",
]


def looks_like_broad_query(query: str) -> bool:
    normalized = (query or "").strip().lower()
    if not normalized:
        return True
    if any(term in normalized for term in BROAD_QUERY_TERMS):
        return True
    broad_signals = [
        "course materials",
        "course resources",
        "study resources",
        "学习资料",
        "课程资料",
        "公开学习资源",
        "参考资料",
    ]
    return any(signal in normalized for signal in broad_signals) and "github" not in normalized and "repo" not in normalized


def infer_risk_flags(query: str, item: SearchResultItem, usable_parts: list[str]) -> list[str]:
    text = " ".join(
        [
            query or "",
            item.title or "",
            item.url or "",
            item.snippet or "",
            item.explanation or "",
            item.why_recommended or "",
            *(item.reference_utility or []),
            *usable_parts,
        ]
    ).lower()

    flags: list[str] = []

    if _is_unsupported_source(item):
        flags.extend(["unsupported_source", "low_confidence"])

    if _is_repository_source(item):
        flags.append("not_official")

    if any(term in text for term in COPY_RISK_TERMS):
        flags.append("copy_risk")

    if looks_like_broad_query(query):
        flags.append("broad_query")

    if not item.title or not item.url:
        flags.append("unknown_source")

    if _is_low_confidence(item, usable_parts):
        flags.append("low_confidence")

    if _may_be_outdated(item):
        flags.append("may_be_outdated")

    if not item.source_type or item.source_type == "unknown":
        flags.append("unknown_source")

    return unique_preserve_order(flags)


def _is_repository_source(item: SearchResultItem) -> bool:
    source_type = (item.source_type or "").lower()
    url = item.url or ""
    return "github" in source_type or is_github_repo_url(url)


def _is_unsupported_source(item: SearchResultItem) -> bool:
    source_type = (item.source_type or "").lower()
    url = (item.url or "").strip()
    if source_type == "unsupported_source":
        return True
    return bool(url) and url.startswith(("http://", "https://")) and not is_github_repo_url(url)


def _is_low_confidence(item: SearchResultItem, usable_parts: list[str]) -> bool:
    if item.score is not None and item.score < 0.45:
        return True
    if item.confidence < 0.45:
        return True
    weak_fields = sum(
        1
        for value in [item.title, item.url, item.explanation, item.why_recommended, item.snippet]
        if value
    )
    return weak_fields <= 2 or not usable_parts


def _may_be_outdated(item: SearchResultItem) -> bool:
    if item.updated_at:
        return False
    current_year = datetime.now(timezone.utc).year
    if item.year is not None:
        return item.year < current_year - 4
    return True
