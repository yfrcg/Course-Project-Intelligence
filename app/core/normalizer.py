from __future__ import annotations

from typing import Any, Iterable, List, Optional
from urllib.parse import urlparse

from app.core.university_profiles import get_university_profile
from app.core.vocabulary import find_course, find_school, find_tech_keywords, term_in_text
from app.schemas import ProviderSearchResult, SearchResultItem
from app.utils.text import guess_year, normalize_url_key, truncate_text


REPO_TYPE_USE_CASE = {
    "lab_code": "适合参考实验代码结构、模块拆分和实现路径。",
    "course_project": "适合参考课程项目选题、模块边界和技术路线。",
    "report_only": "适合参考报告结构与文档组织，不适合直接借鉴实现代码。",
    "notes": "适合参考课程笔记、知识点整理和复习结构。",
    "exam_solution": "适合题型调研和知识点核对，不适合作为实验或项目直接参考。",
    "collection": "适合做课程资料导航和继续深挖，不一定是单仓最佳参考。",
    "org_meta": "这是组织元信息仓库，不适合作为具体课程项目参考。",
    "generic_algorithm": "更像通用算法资料仓库，课程针对性有限。",
    "unknown": "适合做前期调研，但仍需要人工核实内容质量。",
}

DEFAULT_CAVEAT = "适合学习参考，不建议直接复用仓库代码、报告或答案作为作业提交。"


def _identifier_variant(text: str) -> str:
    return (
        (text or "")
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace(".", " ")
    )


def _metadata_value(metadata: dict[str, Any], key: str) -> Any:
    return metadata[key] if key in metadata else None


def _primary_language(metadata: dict[str, Any]) -> str | None:
    languages = metadata.get("languages")
    if isinstance(languages, list):
        for language in languages:
            if language:
                return str(language)
    language = metadata.get("language")
    return str(language) if language else None


def infer_source_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "github.com" in host:
        return "github"
    if "gitee.com" in host:
        return "gitee"
    return host or "web"


def infer_source_type(url: str, source_type: str | None = None) -> str:
    if source_type:
        return source_type
    source = infer_source_from_url(url)
    if source in {"github", "gitee"}:
        return source
    return "web"


def infer_tech_tags(title: str, snippet: str, metadata: dict[str, Any]) -> List[str]:
    combined = " ".join(
        [
            title or "",
            snippet or "",
            " ".join(metadata.get("topics", []) or []),
            " ".join(metadata.get("languages", []) or []),
            metadata.get("readme_excerpt", "") or "",
        ]
    )
    return find_tech_keywords(combined)


def infer_use_case(title: str, snippet: str, metadata: dict[str, Any], repo_type: str | None) -> str:
    if repo_type:
        return REPO_TYPE_USE_CASE.get(repo_type, REPO_TYPE_USE_CASE["unknown"])

    text = f"{title} {snippet}".lower()
    if "report" in text or "报告" in text:
        return REPO_TYPE_USE_CASE["report_only"]
    if "lab" in text or "实验" in text:
        return REPO_TYPE_USE_CASE["lab_code"]
    if "course project" in text or "大作业" in text or "课程设计" in text:
        return REPO_TYPE_USE_CASE["course_project"]
    return REPO_TYPE_USE_CASE["unknown"]


def default_risk_note(source_type: str, title: str = "", snippet: str = "", repo_type: str | None = None) -> str:
    text = f"{title} {snippet}".lower()
    if repo_type == "exam_solution" or "answer" in text or "答案" in text or "solution" in text:
        return "仅供学习参考和知识点核对，不建议直接复用答案或题解内容。"
    if repo_type == "org_meta":
        return "该仓库偏组织元信息，不代表具体课程实现质量。"
    if source_type in {"github", "gitee"}:
        return DEFAULT_CAVEAT
    return "请结合课程要求甄别资料时效性与适用性，避免直接照搬。"


def normalize_provider_result(
    item: ProviderSearchResult,
    *,
    school: str | None = None,
    course: str | None = None,
    confidence: float = 0.0,
    explanation: str = "",
    evidence: Optional[dict[str, Any]] = None,
) -> SearchResultItem:
    metadata = dict(item.metadata or {})
    title = item.title or item.url
    snippet = truncate_text(item.snippet or "", 1200)
    detection_text = " ".join(
        [
            title,
            snippet,
            metadata.get("full_name", "") or "",
            metadata.get("owner", "") or "",
            metadata.get("readme_excerpt", "") or "",
            _identifier_variant(title),
            _identifier_variant(metadata.get("full_name", "") or ""),
            _identifier_variant(" ".join(metadata.get("root_paths", []) or [])),
        ]
    )

    year = metadata.get("year") or guess_year(f"{title} {snippet}")
    inferred_school = metadata.get("school") or find_school(detection_text)
    inferred_course = metadata.get("course") or find_course(detection_text)
    if not inferred_school and school and term_in_text(detection_text, school):
        inferred_school = school
    if not inferred_course and course and term_in_text(detection_text, course):
        inferred_course = course

    evidence = dict(evidence or {})
    detected_school = evidence.get("detected_school") or inferred_school
    detected_school_id = evidence.get("detected_school_id")
    if not detected_school_id and detected_school:
        profile = get_university_profile(detected_school)
        detected_school_id = profile.id if profile else None
    repo_type = evidence.get("repo_type") or metadata.get("repo_type")
    positive_evidence = list(evidence.get("positive_evidence") or [])
    negative_evidence = list(evidence.get("negative_evidence") or [])
    reference_utility = list(evidence.get("reference_utility") or [])
    why_recommended = evidence.get("why_recommended") or explanation or None
    matched_school = evidence.get("matched_school")
    matched_course = evidence.get("matched_course") or inferred_course
    matched_intent = evidence.get("matched_intent") or None
    source_provider = evidence.get("source_provider") or item.source or infer_source_from_url(item.url)
    school_evidence = list(evidence.get("school_evidence") or [])
    school_match_strength = evidence.get("school_match_strength") or None
    matched_school_aliases = list(evidence.get("matched_school_aliases") or [])
    caveat = evidence.get("caveat") or default_risk_note(item.source_type, title, snippet, repo_type)
    value_level = evidence.get("value_level") or None
    confidence_level = evidence.get("confidence_level") or None
    cap_reason = evidence.get("cap_reason") or None

    return SearchResultItem(
        title=title,
        url=item.url,
        source=item.source or infer_source_from_url(item.url),
        source_type=infer_source_type(item.url, item.source_type),
        repo=str(metadata.get("full_name") or "") or None,
        snippet=snippet,
        school=detected_school,
        school_id=detected_school_id,
        course=inferred_course,
        tech_tags=infer_tech_tags(title, snippet, metadata),
        year=year,
        confidence=confidence,
        score=confidence,
        use_case=infer_use_case(title, snippet, metadata, repo_type),
        risk_note=caveat,
        explanation=explanation,
        description=metadata.get("description") or None,
        language=_primary_language(metadata),
        updated_at=_metadata_value(metadata, "updated_at"),
        stars=_metadata_value(metadata, "stargazers_count"),
        intent=matched_intent,
        repo_type=repo_type,
        value_level=value_level,
        confidence_level=confidence_level,
        why_recommended=why_recommended,
        positive_evidence=positive_evidence[:5],
        negative_evidence=negative_evidence[:3],
        reference_utility=reference_utility[:4],
        cap_reason=cap_reason,
        caveat=caveat,
        matched_school=matched_school,
        school_evidence=school_evidence[:5],
        school_match_strength=school_match_strength,
        matched_school_aliases=matched_school_aliases[:5],
        matched_course=matched_course,
        matched_intent=matched_intent,
        source_provider=source_provider,
        debug=evidence,
        metadata=metadata,
    )


def dedupe_results(items: Iterable[SearchResultItem]) -> List[SearchResultItem]:
    seen: set[str] = set()
    result: List[SearchResultItem] = []
    for item in items:
        key = normalize_url_key(item.url)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
