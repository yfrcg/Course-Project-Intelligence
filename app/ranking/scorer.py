from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.core.course_profiles import (
    course_negative_signal_hits,
    course_structure_hits,
    detect_course_specific_assets,
    detect_courses,
    get_course_profile,
)
from app.core.repo_classifier import (
    REPO_TYPE_COLLECTION,
    REPO_TYPE_COURSE_PROJECT,
    REPO_TYPE_EXAM_SOLUTION,
    REPO_TYPE_GENERIC_ALGORITHM,
    REPO_TYPE_LAB_CODE,
    REPO_TYPE_NOTES,
    REPO_TYPE_ORG_META,
    REPO_TYPE_REPORT_ONLY,
    REPO_TYPE_UNKNOWN,
    classify_repository,
)
from app.core.retrieval_intents import (
    INTENT_COLLECTION,
    INTENT_EXAM,
    INTENT_GENERIC,
    INTENT_LAB,
    INTENT_NOTES,
    INTENT_PROJECT,
    classify_query_intent,
)
from app.core.university_profiles import (
    BROAD_SCHOOL_SCOPE_KINDS,
    UniversityMatch,
    UniversityProfile,
    count_university_term_occurrences,
    detect_university_matches,
    group_for_school_scope,
    get_university_profile,
    is_broad_school_scope,
    list_university_profiles,
    profile_in_group,
)
from app.core.vocabulary import count_term_hits, find_course, get_course_aliases, term_in_text
from app.ranking.ranking_policy import (
    FRESHNESS_POPULARITY_WEIGHTS,
    RAW_SCORE_WEIGHTS,
    RELEVANCE_WEIGHTS,
    SCORE_CAPS,
    SOURCE_VALUE_WEIGHTS,
    VALUE_LEVEL_THRESHOLDS,
    resolve_domain_trust,
    resolve_platform_trust,
)
from app.ranking.types import EvidenceBundle, ScoreBreakdown, ScoreExplanation
from app.schemas import ProviderSearchResult, QueryAnalysis
from app.utils.text import safe_lower, unique_preserve_order


DEFAULT_CAVEAT = "仅用于课程项目调研和学习参考，不建议直接复用代码、报告或答案作为作业提交。"

REPO_TYPE_TO_INTENT = {
    REPO_TYPE_LAB_CODE: INTENT_LAB,
    REPO_TYPE_COURSE_PROJECT: INTENT_PROJECT,
    REPO_TYPE_NOTES: INTENT_NOTES,
    REPO_TYPE_REPORT_ONLY: INTENT_NOTES,
    REPO_TYPE_EXAM_SOLUTION: INTENT_EXAM,
    REPO_TYPE_COLLECTION: INTENT_COLLECTION,
    REPO_TYPE_GENERIC_ALGORITHM: INTENT_GENERIC,
    REPO_TYPE_ORG_META: INTENT_GENERIC,
    REPO_TYPE_UNKNOWN: INTENT_GENERIC,
}

INTENT_REPO_COMPATIBILITY = {
    INTENT_LAB: {
        REPO_TYPE_LAB_CODE: 1.00,
        REPO_TYPE_COURSE_PROJECT: 0.84,
        REPO_TYPE_REPORT_ONLY: 0.52,
        REPO_TYPE_NOTES: 0.40,
        REPO_TYPE_EXAM_SOLUTION: 0.22,
        REPO_TYPE_COLLECTION: 0.30,
        REPO_TYPE_GENERIC_ALGORITHM: 0.26,
        REPO_TYPE_ORG_META: 0.12,
        REPO_TYPE_UNKNOWN: 0.42,
    },
    INTENT_PROJECT: {
        REPO_TYPE_COURSE_PROJECT: 1.00,
        REPO_TYPE_LAB_CODE: 0.86,
        REPO_TYPE_REPORT_ONLY: 0.58,
        REPO_TYPE_NOTES: 0.42,
        REPO_TYPE_EXAM_SOLUTION: 0.22,
        REPO_TYPE_COLLECTION: 0.36,
        REPO_TYPE_GENERIC_ALGORITHM: 0.28,
        REPO_TYPE_ORG_META: 0.12,
        REPO_TYPE_UNKNOWN: 0.46,
    },
    INTENT_NOTES: {
        REPO_TYPE_NOTES: 1.00,
        REPO_TYPE_REPORT_ONLY: 0.76,
        REPO_TYPE_COLLECTION: 0.44,
        REPO_TYPE_COURSE_PROJECT: 0.42,
        REPO_TYPE_LAB_CODE: 0.36,
        REPO_TYPE_EXAM_SOLUTION: 0.18,
        REPO_TYPE_GENERIC_ALGORITHM: 0.24,
        REPO_TYPE_ORG_META: 0.12,
        REPO_TYPE_UNKNOWN: 0.42,
    },
    INTENT_EXAM: {
        REPO_TYPE_EXAM_SOLUTION: 1.00,
        REPO_TYPE_COLLECTION: 0.62,
        REPO_TYPE_NOTES: 0.46,
        REPO_TYPE_REPORT_ONLY: 0.46,
        REPO_TYPE_COURSE_PROJECT: 0.32,
        REPO_TYPE_LAB_CODE: 0.28,
        REPO_TYPE_GENERIC_ALGORITHM: 0.32,
        REPO_TYPE_ORG_META: 0.10,
        REPO_TYPE_UNKNOWN: 0.36,
    },
    INTENT_COLLECTION: {
        REPO_TYPE_COLLECTION: 1.00,
        REPO_TYPE_NOTES: 0.74,
        REPO_TYPE_REPORT_ONLY: 0.62,
        REPO_TYPE_COURSE_PROJECT: 0.54,
        REPO_TYPE_LAB_CODE: 0.50,
        REPO_TYPE_EXAM_SOLUTION: 0.46,
        REPO_TYPE_GENERIC_ALGORITHM: 0.40,
        REPO_TYPE_ORG_META: 0.18,
        REPO_TYPE_UNKNOWN: 0.44,
    },
    INTENT_GENERIC: {
        REPO_TYPE_COURSE_PROJECT: 0.64,
        REPO_TYPE_LAB_CODE: 0.64,
        REPO_TYPE_NOTES: 0.62,
        REPO_TYPE_REPORT_ONLY: 0.56,
        REPO_TYPE_EXAM_SOLUTION: 0.42,
        REPO_TYPE_COLLECTION: 0.52,
        REPO_TYPE_GENERIC_ALGORITHM: 0.42,
        REPO_TYPE_ORG_META: 0.18,
        REPO_TYPE_UNKNOWN: 0.48,
    },
}

POSITIVE_EVIDENCE_LIMIT = 5
NEGATIVE_EVIDENCE_LIMIT = 3


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _round_score(value: float) -> float:
    return round(_clamp(value), 4)


def _dedupe_reasons_case_insensitive(reasons: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        normalized = " ".join(safe_lower(reason).split())
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(reason)
    return deduped


def _metadata_values(metadata: dict[str, Any], key: str) -> list[str]:
    value = metadata.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


def _root_signal(metadata: dict[str, Any]) -> dict[str, Any]:
    signal = metadata.get("root_signal")
    return dict(signal) if isinstance(signal, dict) else {}


def _root_paths(metadata: dict[str, Any]) -> list[str]:
    return _metadata_values(metadata, "root_paths")


def _root_dir_names(metadata: dict[str, Any]) -> list[str]:
    names = _metadata_values(metadata, "root_dir_names")
    return names or _metadata_values(metadata, "root_dirs")


def _root_file_names(metadata: dict[str, Any]) -> list[str]:
    names = _metadata_values(metadata, "root_file_names")
    return names or _metadata_values(metadata, "root_files")


def _identifier_variant(text: str) -> str:
    return (
        (text or "")
        .replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace(".", " ")
    )


def _joined_candidate_text(item: ProviderSearchResult) -> str:
    metadata = dict(item.metadata or {})
    parts = [
        item.title or "",
        _identifier_variant(item.title or ""),
        str(metadata.get("full_name") or ""),
        _identifier_variant(str(metadata.get("full_name") or "")),
        str(metadata.get("description") or ""),
        item.snippet or "",
        str(metadata.get("readme_text") or ""),
        str(metadata.get("readme_summary") or ""),
        str(metadata.get("readme_excerpt") or ""),
        " ".join(_root_paths(metadata)),
        " ".join(_root_dir_names(metadata)),
        " ".join(_root_file_names(metadata)),
        " ".join(_metadata_values(metadata, "topics")),
        " ".join(_metadata_values(metadata, "languages")),
    ]
    return " ".join(part for part in parts if part).strip()


def _repo_title_text(item: ProviderSearchResult) -> str:
    metadata = dict(item.metadata or {})
    return " ".join(
        part
        for part in [
            item.title or "",
            _identifier_variant(item.title or ""),
            str(metadata.get("full_name") or ""),
            _identifier_variant(str(metadata.get("full_name") or "")),
        ]
        if part
    )


def _description_text(item: ProviderSearchResult) -> str:
    metadata = dict(item.metadata or {})
    return " ".join(
        part
        for part in [
            str(metadata.get("description") or ""),
            item.snippet or "",
        ]
        if part
    )


def _readme_text(metadata: dict[str, Any]) -> str:
    return str(
        metadata.get("readme_text")
        or metadata.get("readme_summary")
        or metadata.get("readme_excerpt")
        or ""
    )


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _days_since(value: str | None) -> int | None:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    now = datetime.now(UTC)
    return max(0, (now - parsed).days)


def _source_provider(item: ProviderSearchResult) -> str:
    if item.source:
        return item.source
    host = urlparse(item.url or "").netloc.lower()
    if "github.com" in host:
        return "github"
    if "gitee.com" in host:
        return "gitee"
    if "gitlab.com" in host:
        return "gitlab"
    return "web"


def _target_school_profile(analysis: QueryAnalysis) -> UniversityProfile | None:
    if analysis.school_id:
        return get_university_profile(analysis.school_id)
    if analysis.school:
        return get_university_profile(analysis.school)
    if len(analysis.detected_school_ids) == 1:
        return get_university_profile(analysis.detected_school_ids[0])
    return None


def _broad_scope_group(analysis: QueryAnalysis) -> str | None:
    return group_for_school_scope(analysis.school_scope)


def _scope_group_match(
    analysis: QueryAnalysis,
    detected_match: UniversityMatch | None,
) -> str:
    group = _broad_scope_group(analysis)
    if not group:
        return "not_applicable"
    if detected_match is None or not detected_match.matched_aliases:
        return "unknown"
    if profile_in_group(detected_match.profile, group):
        return "matched"
    return "outside_scope"


def _school_alias_hits(profile: UniversityProfile, text: str) -> list[str]:
    matched: list[str] = []
    for alias in profile.all_aliases():
        if term_in_text(text, alias):
            matched.append(alias)
    return unique_preserve_order(matched)


def _evaluate_school_profile(
    item: ProviderSearchResult,
    profile: UniversityProfile,
    *,
    query_has_school: bool,
) -> UniversityMatch | None:
    metadata = dict(item.metadata or {})
    title_text = _repo_title_text(item)
    description_text = _description_text(item)
    readme_text = _readme_text(metadata)
    root_text = " ".join(_root_paths(metadata) + _root_dir_names(metadata) + _root_file_names(metadata))

    matched_aliases: list[str] = []
    ambiguous_aliases: list[str] = []
    evidence: list[str] = []
    has_canonical_name = False
    has_english_name = False
    ambiguous_alias_set = profile.ambiguous_alias_set()

    def _alias_sort_key(alias: str) -> tuple[int, int]:
        lowered = safe_lower(alias)
        if lowered == safe_lower(profile.canonical_name):
            return (0, -len(alias))
        if lowered == safe_lower(profile.english_name):
            return (1, -len(alias))
        return (2, -len(alias))

    for alias in sorted(profile.all_aliases(), key=_alias_sort_key):
        if any(
            not alias.isascii() and not matched_alias.isascii() and alias in matched_alias
            for matched_alias in matched_aliases
        ):
            continue
        if term_in_text(title_text, alias):
            matched_aliases.append(alias)
            evidence.append(f"repo name contains {alias}")
        if term_in_text(description_text, alias):
            matched_aliases.append(alias)
            evidence.append(f"description contains {alias}")
        readme_count = count_university_term_occurrences(readme_text, alias)
        if readme_count > 1:
            matched_aliases.append(alias)
            evidence.append(f"README mentions {alias} {readme_count} times")
        elif readme_count == 1:
            matched_aliases.append(alias)
            evidence.append(f"README contains {alias}")
        if term_in_text(root_text, alias):
            matched_aliases.append(alias)
            evidence.append(f"root entries contain {alias}")
        lowered = safe_lower(alias)
        if lowered == safe_lower(profile.canonical_name):
            has_canonical_name = has_canonical_name or alias in matched_aliases
        if lowered == safe_lower(profile.english_name):
            has_english_name = has_english_name or alias in matched_aliases
        if lowered in ambiguous_alias_set and alias in matched_aliases:
            ambiguous_aliases.append(alias)

    matched_aliases = unique_preserve_order(matched_aliases)
    ambiguous_aliases = unique_preserve_order(ambiguous_aliases)
    if not matched_aliases:
        if query_has_school:
            return UniversityMatch(
                profile=profile,
                matched_aliases=[],
                ambiguous_aliases=[],
                evidence=[],
                has_canonical_name=False,
                has_english_name=False,
            )
        return None

    return UniversityMatch(
        profile=profile,
        matched_aliases=matched_aliases,
        ambiguous_aliases=ambiguous_aliases,
        evidence=unique_preserve_order(evidence),
        has_canonical_name=has_canonical_name,
        has_english_name=has_english_name,
    )


def _select_best_school_match(
    analysis: QueryAnalysis,
    item: ProviderSearchResult,
) -> tuple[UniversityMatch | None, UniversityMatch | None]:
    target_profile = _target_school_profile(analysis)
    target_match = None
    if target_profile is not None:
        target_match = _evaluate_school_profile(
            item,
            target_profile,
            query_has_school=True,
        )

    best_detected = None
    for profile in list_university_profiles():
        if target_profile is not None and profile.id == target_profile.id:
            current = target_match
        else:
            current = _evaluate_school_profile(
                item,
                profile,
                query_has_school=False,
            )
        if current is None or not current.matched_aliases:
            continue
        if best_detected is None or current.score() > best_detected.score():
            best_detected = current
    return target_match, best_detected


def _school_match_strength(match: UniversityMatch | None) -> str:
    if match is None or not match.matched_aliases:
        return "none"

    evidence_text = " ".join(match.evidence)
    readme_mentions = sum(1 for evidence in match.evidence if evidence.startswith("README"))
    repo_or_desc = any(
        evidence.startswith("repo name contains") or evidence.startswith("description contains")
        for evidence in match.evidence
    )
    root_hit = any(evidence.startswith("root entries contain") for evidence in match.evidence)
    has_full_name = match.has_canonical_name or match.has_english_name

    if match.ambiguous and not has_full_name:
        return "ambiguous"
    if repo_or_desc or (readme_mentions >= 2) or (readme_mentions >= 1 and root_hit):
        return "strong"
    if "README mentions" in evidence_text or "README contains" in evidence_text or root_hit:
        return "weak"
    return "weak"


def _compute_school_score(
    analysis: QueryAnalysis,
    target_match: UniversityMatch | None,
    detected_match: UniversityMatch | None,
) -> tuple[float, str, list[str], list[str], str | None, str | None]:
    query_has_school = _target_school_profile(analysis) is not None
    selected = target_match if query_has_school else detected_match
    matched_school = None
    detected_school = None
    detected_school_id = None
    if selected is not None and selected.matched_aliases:
        detected_school = selected.profile.canonical_name
        detected_school_id = selected.profile.id
    elif detected_match is not None and detected_match.matched_aliases:
        detected_school = detected_match.profile.canonical_name
        detected_school_id = detected_match.profile.id

    if query_has_school:
        matched_school = analysis.school
        strength = _school_match_strength(target_match)
        evidence = list(target_match.evidence if target_match is not None else [])
        aliases = list(target_match.matched_aliases if target_match is not None else [])
        if strength == "strong":
            return 1.0, strength, evidence, aliases, matched_school, detected_school
        if strength == "weak":
            return 0.65, strength, evidence, aliases, matched_school, detected_school
        if strength == "ambiguous":
            return 0.56, strength, evidence, aliases, None, detected_school
        return 0.0, "none", [], [], None, detected_school

    broad_scope = is_broad_school_scope(analysis.school_scope)
    broad_group_match = _scope_group_match(analysis, detected_match)
    if detected_match is not None and detected_match.matched_aliases:
        strength = _school_match_strength(detected_match)
        evidence = list(detected_match.evidence)
        aliases = list(detected_match.matched_aliases)
        if broad_scope and broad_group_match == "outside_scope":
            if strength == "strong":
                return 0.46, strength, evidence, aliases, detected_match.profile.canonical_name, detected_school
            if strength == "weak":
                return 0.38, strength, evidence, aliases, detected_match.profile.canonical_name, detected_school
            if strength == "ambiguous":
                return 0.30, strength, evidence, aliases, None, detected_school
        if broad_scope:
            if strength == "strong":
                return 0.76, strength, evidence, aliases, detected_match.profile.canonical_name, detected_school
            if strength == "weak":
                return 0.62, strength, evidence, aliases, detected_match.profile.canonical_name, detected_school
            if strength == "ambiguous":
                return 0.48, strength, evidence, aliases, None, detected_school
        if strength == "strong":
            return 0.76, strength, evidence, aliases, detected_match.profile.canonical_name, detected_school
        if strength == "weak":
            return 0.64, strength, evidence, aliases, detected_match.profile.canonical_name, detected_school
        if strength == "ambiguous":
            return 0.58, strength, evidence, aliases, None, detected_school
    if broad_scope:
        return 0.28, "none", [], [], None, None
    return 0.55, "none", [], [], None, None


def _course_hits_by_region(aliases: list[str], *, title_text: str, description_text: str, readme_text: str, root_text: str) -> dict[str, list[str]]:
    hits = {"title": [], "description": [], "readme": [], "root": []}
    for alias in aliases:
        if term_in_text(title_text, alias):
            hits["title"].append(alias)
        if term_in_text(description_text, alias):
            hits["description"].append(alias)
        if term_in_text(readme_text, alias):
            hits["readme"].append(alias)
        if term_in_text(root_text, alias):
            hits["root"].append(alias)
    return {key: unique_preserve_order(value) for key, value in hits.items()}


def _compute_course_score(
    analysis: QueryAnalysis,
    item: ProviderSearchResult,
    positive_evidence: list[str],
    *,
    course_profile=None,
    course_specific_assets: dict[str, bool] | None = None,
) -> tuple[float, str | None]:
    metadata = dict(item.metadata or {})
    target_profile = course_profile or get_course_profile(analysis.course_profile_id or analysis.course)
    if target_profile is None:
        detected_profiles = detect_courses(_joined_candidate_text(item))
        target_profile = detected_profiles[0] if detected_profiles else None
    if target_profile is None:
        return 0.55, None

    target_course = target_profile.canonical_name
    aliases = get_course_aliases(target_course)
    title_text = _repo_title_text(item)
    description_text = _description_text(item)
    readme_text = _readme_text(metadata)
    root_text = " ".join(_root_paths(metadata) + _root_dir_names(metadata) + _root_file_names(metadata))
    structure_hits = course_structure_hits(target_profile, " ".join([title_text, description_text, readme_text, root_text]), limit=4)
    assets = dict(course_specific_assets or {})
    hits = _course_hits_by_region(
        aliases,
        title_text=title_text,
        description_text=description_text,
        readme_text=readme_text,
        root_text=root_text,
    )

    weak_aliases = target_profile.weak_alias_set()
    title_or_description_hits = unique_preserve_order(hits["title"] + hits["description"])
    strong_metadata_hits = [
        alias for alias in title_or_description_hits if safe_lower(alias) not in weak_aliases
    ]
    strong_root_hits = [alias for alias in hits["root"] if safe_lower(alias) not in weak_aliases]
    strong_readme_hits = [alias for alias in hits["readme"] if safe_lower(alias) not in weak_aliases]

    if strong_metadata_hits:
        alias = strong_metadata_hits[0]
        positive_evidence.append(f"course alias {alias} appears in repo metadata")
        return 1.0, target_course
    if title_or_description_hits and structure_hits:
        positive_evidence.append(
            f"course metadata and structure signals match {', '.join(structure_hits[:2])}"
        )
        return 0.90, target_course
    if strong_root_hits:
        positive_evidence.append(f"course alias {strong_root_hits[0]} appears in root entries")
        return 0.88, target_course
    if len(strong_readme_hits) >= 2:
        positive_evidence.append(f"README repeatedly mentions course alias {strong_readme_hits[0]}")
        return 0.82, target_course
    if strong_readme_hits:
        positive_evidence.append(f"README contains course alias {strong_readme_hits[0]}")
        return 0.68, target_course
    asset_hit_count = sum(1 for value in assets.values() if value)
    if asset_hit_count >= 2 and structure_hits:
        positive_evidence.append(
            f"course structure signals match {', '.join(structure_hits[:2])}"
        )
        return 0.74, target_course
    if structure_hits:
        positive_evidence.append(f"course structure signals match {', '.join(structure_hits[:2])}")
        return 0.64, target_course
    if title_or_description_hits or hits["readme"]:
        alias = (title_or_description_hits or hits["readme"])[0]
        positive_evidence.append(f"course alias {alias} appears with limited specificity")
        return 0.60, target_course
    if analysis.course:
        return 0.02, None
    return 0.55, target_course


def _query_keywords(analysis: QueryAnalysis) -> list[str]:
    keywords = [
        *analysis.project_keywords,
        *analysis.tech_keywords,
        *analysis.resource_keywords,
    ]
    generic_keywords = {
        "github",
        "gitee",
        "gitlab",
        "repo",
        "repository",
        "tutorial",
        "resource",
        "resources",
    }
    result: list[str] = []
    for keyword in unique_preserve_order(keywords):
        normalized = safe_lower(keyword)
        if normalized.isascii() and len(normalized) <= 1:
            continue
        if normalized in generic_keywords:
            continue
        result.append(keyword)
    return result[:10]


def _compute_keyword_score(
    analysis: QueryAnalysis,
    item: ProviderSearchResult,
    positive_evidence: list[str],
) -> float:
    keywords = _query_keywords(analysis)
    if not keywords:
        return 0.55

    text = _joined_candidate_text(item)
    hit_count = count_term_hits(text, keywords)
    if hit_count <= 0:
        return 0.12

    if hit_count >= max(2, len(keywords) // 2):
        positive_evidence.append(f"keyword coverage {hit_count}/{len(keywords)}")
    return _clamp(0.15 + 0.85 * (hit_count / max(1, len(keywords))))


def _collect_structure_positive_evidence(
    metadata: dict[str, Any],
    *,
    query_intent: str,
) -> list[str]:
    signal = _root_signal(metadata)
    ordered_parts: list[str] = []
    if query_intent == INTENT_LAB:
        ordered_parts.extend(
            part
            for part in ("lab", "src", "report")
            if (part == "lab" and signal.get("has_lab_dir"))
            or (part == "src" and signal.get("has_src_dir"))
            or (part == "report" and signal.get("has_report_dir"))
        )
    elif query_intent == INTENT_PROJECT:
        ordered_parts.extend(
            part
            for part in ("src", "report", "sql/schema")
            if (part == "src" and signal.get("has_src_dir"))
            or (part == "report" and signal.get("has_report_dir"))
            or (part == "sql/schema" and signal.get("has_sql_or_schema"))
        )
    elif query_intent == INTENT_NOTES:
        ordered_parts.extend(
            part
            for part in ("notes/docs", "chapter markdown")
            if (part == "notes/docs" and signal.get("has_notes_dir"))
            or (part == "chapter markdown" and (signal.get("markdown_file_count") or 0) >= 2)
        )
    elif query_intent == INTENT_EXAM:
        if signal.get("has_exam_dir"):
            ordered_parts.append("exam")
    else:
        ordered_parts.extend(
            part
            for part in ("src", "lab", "report", "notes/docs")
            if (part == "src" and signal.get("has_src_dir"))
            or (part == "lab" and signal.get("has_lab_dir"))
            or (part == "report" and signal.get("has_report_dir"))
            or (part == "notes/docs" and signal.get("has_notes_dir"))
        )

    reasons: list[str] = []
    if ordered_parts:
        reasons.append(f"root entries contain {'/'.join(ordered_parts)}")
    if signal.get("has_sql_or_schema") and "sql/schema" not in ordered_parts:
        reasons.append("root entries contain sql/schema")
    if signal.get("has_package_or_requirements"):
        reasons.append("root entries contain package/requirements files")
    return reasons[:3]


def _collect_content_positive_evidence(metadata: dict[str, Any]) -> list[str]:
    readme_text = safe_lower(_readme_text(metadata))
    reasons: list[str] = []
    if any(term in readme_text for term in ("usage", "how to run", "run", "install", "requirements", "环境", "运行")):
        reasons.append("README includes run/setup instructions")
    if any(term in readme_text for term in ("structure", "目录", "module", "modules", "chapter", "章节")):
        reasons.append("README explains repository structure")
    return reasons[:2]


def _positive_evidence_priority(
    reason: str,
    *,
    school_evidence: list[str],
    matched_school_aliases: list[str],
    matched_course: str | None,
) -> int:
    lowered = safe_lower(reason)
    if reason in school_evidence:
        return 0
    if any(alias and safe_lower(alias) in lowered for alias in matched_school_aliases):
        return 0
    if matched_course and safe_lower(matched_course) in lowered:
        return 1
    if "course alias" in lowered:
        return 1
    if any(term in lowered for term in ("query intent", "course project", "final assignment", "notes or lecture", "exam-like", "repo type ")):
        return 2
    if any(term in lowered for term in ("root entries contain", "root contains", "src", "report", "sql/schema", "notes/docs", "package/requirements", "code and report coexist", "project-like src structure", "root contains")):
        return 3
    if any(term in lowered for term in ("readme includes", "readme explains", "readme contains", "readme repeatedly mentions")):
        return 4
    if "keyword coverage" in lowered:
        return 5
    if "public visibility" in lowered:
        return 6
    return 5


def _sort_positive_evidence(
    reasons: list[str],
    *,
    school_evidence: list[str],
    matched_school_aliases: list[str],
    matched_course: str | None,
) -> list[str]:
    unique = _dedupe_reasons_case_insensitive([reason for reason in reasons if reason])
    ranked = sorted(
        enumerate(unique),
        key=lambda item: (
            _positive_evidence_priority(
                item[1],
                school_evidence=school_evidence,
                matched_school_aliases=matched_school_aliases,
                matched_course=matched_course,
            ),
            item[0],
        ),
    )
    return [reason for _, reason in ranked]


def _limit_positive_evidence(
    reasons: list[str],
    *,
    school_evidence: list[str],
    matched_school_aliases: list[str],
    matched_course: str | None,
    limit: int,
) -> list[str]:
    quotas = {
        0: 2,
        1: 1,
        2: 1,
        3: 1,
        4: 1,
        5: 1,
        6: 1,
    }
    selected: list[str] = []
    selected_counts: dict[int, int] = {}
    deferred: list[str] = []

    for reason in reasons:
        bucket = _positive_evidence_priority(
            reason,
            school_evidence=school_evidence,
            matched_school_aliases=matched_school_aliases,
            matched_course=matched_course,
        )
        if selected_counts.get(bucket, 0) < quotas.get(bucket, limit):
            selected.append(reason)
            selected_counts[bucket] = selected_counts.get(bucket, 0) + 1
            if len(selected) >= limit:
                return selected[:limit]
        else:
            deferred.append(reason)

    for reason in deferred:
        if reason in selected:
            continue
        selected.append(reason)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _sort_negative_evidence(reasons: list[str]) -> list[str]:
    def priority(reason: str) -> int:
        lowered = safe_lower(reason)
        if "organization profile" in lowered:
            return 0
        if "lacks target school evidence" in lowered:
            return 1
        if "readme only" in lowered:
            return 2
        if "enrichment failed" in lowered:
            return 3
        return 4

    unique = _dedupe_reasons_case_insensitive([reason for reason in reasons if reason])
    ranked = sorted(enumerate(unique), key=lambda item: (priority(item[1]), item[0]))
    return [reason for _, reason in ranked]


def _strong_alignment_bonus(evidence: EvidenceBundle, metadata: dict[str, Any]) -> float:
    signal = _root_signal(metadata)
    bonus = 0.0
    strong_structure = evidence.structure_quality >= 0.72
    strong_content = evidence.content_richness >= 0.70

    if (
        evidence.school_match_strength == "strong"
        and evidence.course_score >= 0.95
        and evidence.intent_score >= 0.95
    ):
        if strong_structure:
            bonus += 0.08
        elif strong_content:
            bonus += 0.05
    elif (
        evidence.school_match_strength in {"strong", "weak"}
        and evidence.course_score >= 0.95
        and evidence.intent_score >= 0.84
        and (evidence.structure_quality >= 0.58 or strong_content)
    ):
        bonus += 0.03

    if evidence.repo_type == REPO_TYPE_COURSE_PROJECT and signal.get("has_sql_or_schema"):
        bonus += 0.02
    if evidence.repo_type == REPO_TYPE_LAB_CODE and signal.get("has_lab_dir") and signal.get("has_src_dir"):
        bonus += 0.02
    if evidence.repo_type == REPO_TYPE_NOTES and signal.get("has_notes_dir") and (signal.get("markdown_file_count") or 0) >= 2:
        bonus += 0.02
    return min(0.10, bonus)


def _intent_bonus_from_structure(query_intent: str, signal: dict[str, Any]) -> float:
    if query_intent == INTENT_LAB and (signal.get("has_lab_dir") or signal.get("has_src_dir")):
        return 0.08
    if query_intent == INTENT_PROJECT and (signal.get("has_src_dir") and signal.get("has_report_dir")):
        return 0.07
    if query_intent == INTENT_NOTES and (signal.get("has_notes_dir") or (signal.get("markdown_file_count") or 0) >= 2):
        return 0.08
    if query_intent == INTENT_EXAM and signal.get("has_exam_dir"):
        return 0.08
    if query_intent == INTENT_COLLECTION and signal.get("has_multiple_course_dirs"):
        return 0.08
    return 0.0


def _compute_intent_score(
    analysis: QueryAnalysis,
    repo_type: str,
    signal: dict[str, Any],
    positive_evidence: list[str],
) -> tuple[float, str | None]:
    query_intent = classify_query_intent(analysis)
    matched_intent = query_intent if query_intent != INTENT_GENERIC else REPO_TYPE_TO_INTENT.get(repo_type)
    base_score = INTENT_REPO_COMPATIBILITY.get(query_intent, INTENT_REPO_COMPATIBILITY[INTENT_GENERIC]).get(
        repo_type,
        0.42,
    )
    score = _clamp(base_score + _intent_bonus_from_structure(query_intent, signal))

    if query_intent == INTENT_GENERIC:
        return score, matched_intent
    if matched_intent == query_intent:
        positive_evidence.append(f"repo type {repo_type} matches query intent {query_intent}")
    elif base_score <= 0.4:
        positive_evidence.append(f"repo type {repo_type} is only weakly aligned with query intent {query_intent}")
    return score, matched_intent


def compute_content_richness(candidate: ProviderSearchResult) -> float:
    metadata = dict(candidate.metadata or {})
    readme_text = _readme_text(metadata)
    description = str(metadata.get("description") or "")
    snippet = candidate.snippet or ""
    combined = f"{description} {snippet} {readme_text}".strip()
    if not readme_text and not description and not snippet:
        return 0.10

    word_count = max(len(combined.split()), len(combined) // 12)
    score = 0.12 if not readme_text else 0.25
    if description or snippet:
        score += 0.10
    if word_count >= 20:
        score += 0.20
    if word_count >= 60:
        score += 0.15
    lowered = safe_lower(combined)
    if any(term in lowered for term in ("课程", "course", "实验", "lab", "project", "notes", "作业", "报告", "笔记")):
        score += 0.15
    if any(term in lowered for term in ("运行", "usage", "how to run", "安装", "install", "目录", "structure", "requirements", "chapter", "lecture")):
        score += 0.15
    if not readme_text and any(term in lowered for term in ("课程", "course", "笔记", "notes", "实验", "project")):
        score += 0.18
    if not readme_text and word_count >= 8:
        score += 0.08
    if metadata.get("enrichment_failed"):
        score = min(score, 0.35 if description else 0.22)
    return _clamp(score)


def compute_structure_quality(candidate: ProviderSearchResult, query_context: QueryAnalysis) -> float:
    return _compute_structure_quality(candidate, query_context)


def _course_structure_bonus(course_profile, course_specific_assets: dict[str, bool]) -> float:
    if course_profile is None or not course_specific_assets:
        return 0.0

    if course_profile.id == "database_system":
        return (
            (0.14 if course_specific_assets.get("has_sql_or_schema") else 0.0)
            + (0.08 if course_specific_assets.get("has_models") else 0.0)
            + (0.06 if course_specific_assets.get("has_er_diagram") else 0.0)
        )
    if course_profile.id == "operating_system":
        return (
            (0.12 if course_specific_assets.get("has_kernel_dir") else 0.0)
            + (0.10 if course_specific_assets.get("has_ucore") else 0.0)
            + (0.08 if course_specific_assets.get("has_scheduler_hint") else 0.0)
            + (0.06 if course_specific_assets.get("has_memory_hint") else 0.0)
            + (0.06 if course_specific_assets.get("has_file_system_hint") else 0.0)
        )
    if course_profile.id == "compiler":
        return (
            (0.12 if course_specific_assets.get("has_lexer") else 0.0)
            + (0.12 if course_specific_assets.get("has_parser") else 0.0)
            + (0.08 if course_specific_assets.get("has_ast") else 0.0)
            + (0.08 if course_specific_assets.get("has_ir") else 0.0)
            + (0.06 if course_specific_assets.get("has_llvm") else 0.0)
            + (0.06 if course_specific_assets.get("has_codegen") else 0.0)
        )
    if course_profile.id == "algorithms":
        return (
            (0.12 if course_specific_assets.get("has_chapter_notes") else 0.0)
            + (0.08 if course_specific_assets.get("has_dp_notes") else 0.0)
            + (0.08 if course_specific_assets.get("has_graph_notes") else 0.0)
            + (0.06 if course_specific_assets.get("has_complexity_notes") else 0.0)
        )
    if course_profile.id == "machine_learning":
        return (
            (0.10 if course_specific_assets.get("has_notebook") else 0.0)
            + (0.10 if course_specific_assets.get("has_dataset") else 0.0)
            + (0.10 if course_specific_assets.get("has_train_script") else 0.0)
            + (0.08 if course_specific_assets.get("has_eval_script") else 0.0)
            + (0.06 if course_specific_assets.get("has_model_dir") else 0.0)
        )
    return min(0.18, 0.06 * sum(1 for value in course_specific_assets.values() if value))


def _course_profile_for_item(
    query_context: QueryAnalysis,
    candidate: ProviderSearchResult,
):
    profile = get_course_profile(query_context.course_profile_id or query_context.course)
    if profile is not None:
        return profile
    detected_profiles = detect_courses(_joined_candidate_text(candidate))
    return detected_profiles[0] if detected_profiles else None


def _course_specific_assets_for_item(
    course_profile,
    candidate: ProviderSearchResult,
) -> dict[str, bool]:
    metadata = dict(candidate.metadata or {})
    return detect_course_specific_assets(
        course_profile,
        title=_repo_title_text(candidate),
        description=_description_text(candidate),
        readme_text=_readme_text(metadata),
        root_paths=_root_paths(metadata),
        root_dir_names=_root_dir_names(metadata),
        root_file_names=_root_file_names(metadata),
        root_signal=_root_signal(metadata),
    )


def _compute_structure_quality(
    candidate: ProviderSearchResult,
    query_context: QueryAnalysis,
    *,
    course_profile=None,
    course_specific_assets: dict[str, bool] | None = None,
) -> float:
    metadata = dict(candidate.metadata or {})
    signal = _root_signal(metadata)
    if signal.get("likely_org_meta"):
        return 0.12

    root_paths = _root_paths(metadata)
    if not root_paths and not signal:
        return 0.14

    score = 0.22
    if signal.get("has_readme"):
        score += 0.08

    query_intent = classify_query_intent(query_context)
    if query_intent == INTENT_LAB:
        if signal.get("has_lab_dir"):
            score += 0.28
        if signal.get("has_src_dir"):
            score += 0.22
        if signal.get("has_report_dir"):
            score += 0.08
        if any(term_in_text(" ".join(root_paths), term) for term in ("kernel", "ucore", "test")):
            score += 0.08
    elif query_intent == INTENT_PROJECT:
        if signal.get("has_src_dir"):
            score += 0.24
        if signal.get("has_report_dir"):
            score += 0.16
        if any(term_in_text(" ".join(root_paths), term) for term in ("backend", "frontend", "sql", "schema", "requirements", "package")):
            score += 0.10
    elif query_intent == INTENT_NOTES:
        if signal.get("has_notes_dir"):
            score += 0.28
        if (signal.get("markdown_file_count") or 0) >= 2:
            score += 0.18
        if any(term_in_text(" ".join(root_paths), term) for term in ("lecture", "chapter", "notes", "docs")):
            score += 0.10
        if signal.get("course_specific_paths"):
            score += 0.14
    elif query_intent == INTENT_EXAM:
        if signal.get("has_exam_dir"):
            score += 0.30
        if any(term_in_text(" ".join(root_paths), term) for term in ("paper", "真题", "期末", "midterm", "final")):
            score += 0.12
    elif query_intent == INTENT_COLLECTION:
        if signal.get("has_multiple_course_dirs"):
            score += 0.30
        if signal.get("likely_collection"):
            score += 0.16
    else:
        if signal.get("has_src_dir") or signal.get("has_notes_dir") or signal.get("has_lab_dir"):
            score += 0.20

    if signal.get("likely_collection") and query_intent != INTENT_COLLECTION:
        score -= 0.12
    score += _course_structure_bonus(course_profile, dict(course_specific_assets or {}))
    return _clamp(score)


def compute_course_specificity(candidate: ProviderSearchResult, query_context: QueryAnalysis) -> float:
    return _compute_course_specificity(candidate, query_context)


def _compute_course_specificity(
    candidate: ProviderSearchResult,
    query_context: QueryAnalysis,
    *,
    course_profile=None,
    course_specific_assets: dict[str, bool] | None = None,
) -> float:
    metadata = dict(candidate.metadata or {})
    combined = _joined_candidate_text(candidate)
    description = _description_text(candidate)
    title = _repo_title_text(candidate)
    profile = course_profile or _course_profile_for_item(query_context, candidate)
    course = profile.canonical_name if profile is not None else (query_context.course or find_course(combined))
    signal = _root_signal(metadata)
    if signal.get("likely_org_meta"):
        return 0.10
    if signal.get("likely_collection") or signal.get("has_multiple_course_dirs"):
        return 0.45 if classify_query_intent(query_context) == INTENT_COLLECTION else 0.38
    if (classify_repository(
        title=candidate.title or "",
        description=description,
        readme_text=_readme_text(metadata),
        metadata=metadata,
    ).repo_type == REPO_TYPE_GENERIC_ALGORITHM):
        return 0.25
    if not course:
        return 0.18

    aliases = get_course_aliases(course)
    weak_aliases = profile.weak_alias_set() if profile is not None else set()
    title_or_description = f"{title} {description}"
    strong_metadata_hit = any(
        term_in_text(title_or_description, alias) and safe_lower(alias) not in weak_aliases
        for alias in aliases
    )
    if strong_metadata_hit:
        if query_context.school and query_context.school in combined:
            return 0.92
        return 0.86
    if any(
        term_in_text(_readme_text(metadata), alias) and safe_lower(alias) not in weak_aliases
        for alias in aliases
    ):
        return 0.74
    if any(term_in_text(" ".join(_root_paths(metadata)), alias) for alias in aliases):
        return 0.72
    assets = dict(course_specific_assets or {})
    asset_hit_count = sum(1 for value in assets.values() if value)
    if asset_hit_count >= 3:
        return 0.76
    if asset_hit_count >= 2:
        return 0.68
    return 0.18


def compute_reference_utility(
    candidate: ProviderSearchResult,
    query_context: QueryAnalysis,
) -> tuple[float, list[str]]:
    return _compute_reference_utility(candidate, query_context)


def _course_reference_utility(
    course_profile,
    course_specific_assets: dict[str, bool],
) -> list[str]:
    if course_profile is None:
        return []

    if course_profile.id == "database_system":
        utilities: list[str] = []
        if course_specific_assets.get("has_sql_or_schema"):
            utilities.append("适合参考数据库设计")
        if course_specific_assets.get("has_models"):
            utilities.append("适合参考表结构与 models 映射")
        if course_specific_assets.get("has_er_diagram"):
            utilities.append("适合参考 ER 图")
        return utilities
    if course_profile.id == "operating_system":
        utilities = []
        if course_specific_assets.get("has_kernel_dir") or course_specific_assets.get("has_ucore"):
            utilities.append("适合参考实验流程与内核模块")
        if course_specific_assets.get("has_scheduler_hint"):
            utilities.append("适合参考调度器实现")
        if course_specific_assets.get("has_memory_hint"):
            utilities.append("适合参考内存管理")
        if course_specific_assets.get("has_file_system_hint"):
            utilities.append("适合参考文件系统结构")
        return utilities
    if course_profile.id == "compiler":
        utilities = []
        if course_specific_assets.get("has_lexer"):
            utilities.append("适合参考词法分析")
        if course_specific_assets.get("has_parser"):
            utilities.append("适合参考语法分析")
        if course_specific_assets.get("has_ast"):
            utilities.append("适合参考 AST 组织")
        if course_specific_assets.get("has_ir") or course_specific_assets.get("has_llvm"):
            utilities.append("适合参考 IR/LLVM 管线")
        return utilities
    if course_profile.id == "algorithms":
        utilities = []
        if course_specific_assets.get("has_chapter_notes"):
            utilities.append("适合参考章节笔记结构")
        if course_specific_assets.get("has_dp_notes"):
            utilities.append("适合参考动态规划整理")
        if course_specific_assets.get("has_graph_notes"):
            utilities.append("适合参考图算法整理")
        if course_specific_assets.get("has_complexity_notes"):
            utilities.append("适合参考复杂度分析")
        return utilities
    if course_profile.id == "machine_learning":
        utilities = []
        if course_specific_assets.get("has_dataset"):
            utilities.append("适合参考数据处理")
        if course_specific_assets.get("has_train_script"):
            utilities.append("适合参考模型训练流程")
        if course_specific_assets.get("has_eval_script"):
            utilities.append("适合参考实验评估")
        return utilities
    return list(course_profile.reference_guidance[:2])


def _compute_reference_utility(
    candidate: ProviderSearchResult,
    query_context: QueryAnalysis,
    *,
    course_profile=None,
    course_specific_assets: dict[str, bool] | None = None,
) -> tuple[float, list[str]]:
    metadata = dict(candidate.metadata or {})
    signal = _root_signal(metadata)
    utilities: list[str] = []

    if signal.get("likely_org_meta"):
        return 0.12, ["不建议作为主要参考"]

    utilities.extend(_course_reference_utility(course_profile, dict(course_specific_assets or {})))
    if signal.get("has_lab_dir") or signal.get("has_src_dir"):
        utilities.append("适合参考代码结构")
    if signal.get("has_report_dir"):
        utilities.append("适合参考报告结构")
    if signal.get("has_notes_dir"):
        utilities.append("适合参考学习笔记结构")
    if signal.get("course_specific_paths") and signal.get("has_notes_dir"):
        utilities.append("适合参考章节化课程整理方式")
    root_text = safe_lower(" ".join(_root_paths(metadata)))
    if any(term in root_text for term in ("sql", "schema", "model", "models")):
        utilities.append("适合参考数据库设计")
    readme_text = safe_lower(_readme_text(metadata))
    if any(term in readme_text for term in ("运行", "usage", "how to run", "install", "requirements", "环境")):
        utilities.append("适合参考运行流程")
    if signal.get("likely_collection") and classify_query_intent(query_context) != INTENT_COLLECTION:
        utilities.append("更适合作为资料导航而非单仓主要参考")
    if metadata.get("enrichment_failed"):
        utilities.append("上下文补全失败，需人工复核 README/目录")

    score = 0.18 + 0.16 * min(4, len(utilities))
    if signal.get("has_notes_dir") and (signal.get("markdown_file_count") or 0) >= 2:
        score += 0.18
    if signal.get("has_lab_dir") and signal.get("has_src_dir"):
        score += 0.10
    asset_hit_count = sum(1 for value in (course_specific_assets or {}).values() if value)
    if asset_hit_count >= 2:
        score += 0.12
    elif asset_hit_count == 1:
        score += 0.06
    if signal.get("likely_collection") and classify_query_intent(query_context) != INTENT_COLLECTION:
        score -= 0.12
    if metadata.get("enrichment_failed"):
        score = min(score, 0.40)
    return _clamp(score), unique_preserve_order(utilities)[:4]


def compute_repo_health(candidate: ProviderSearchResult) -> float:
    metadata = dict(candidate.metadata or {})
    if metadata.get("archived"):
        return 0.0

    updated_at = metadata.get("updated_at") or metadata.get("pushed_at")
    age_days = _days_since(updated_at)
    if age_days is None:
        return 0.20
    if age_days <= 183:
        return 0.90
    if age_days <= 365:
        return 0.75
    if age_days <= 730:
        return 0.55
    return 0.30


def _compute_freshness_score(candidate: ProviderSearchResult) -> float:
    metadata = dict(candidate.metadata or {})
    if metadata.get("archived"):
        return 0.0
    age_days = _days_since(metadata.get("updated_at") or metadata.get("pushed_at"))
    if age_days is None:
        return 0.55
    if age_days <= 183:
        return 0.90
    if age_days <= 365:
        return 0.75
    if age_days <= 730:
        return 0.55
    if age_days <= 1095:
        return 0.40
    return 0.25


def _compute_popularity_score(candidate: ProviderSearchResult, positive_evidence: list[str]) -> float:
    metadata = dict(candidate.metadata or {})
    stars = int(metadata.get("stargazers_count") or 0)
    forks = int(metadata.get("forks_count") or 0)
    visibility = stars + forks * 2
    if visibility > 0:
        positive_evidence.append(f"public visibility: stars={stars} forks={forks}")
    if visibility <= 0:
        return 0.18
    return _clamp(0.18 + min(0.48, math.log1p(visibility) / 8.0))


def _readme_only_weak_match(
    analysis: QueryAnalysis,
    item: ProviderSearchResult,
) -> bool:
    metadata = dict(item.metadata or {})
    readme_text = _readme_text(metadata)
    if not readme_text:
        return False
    signal = _root_signal(metadata)
    if signal.get("has_src_dir") or signal.get("has_lab_dir") or signal.get("has_report_dir") or signal.get("has_notes_dir"):
        return False

    title_text = _repo_title_text(item)
    description_text = _description_text(item)
    root_text = " ".join(_root_paths(metadata) + _root_dir_names(metadata) + _root_file_names(metadata))
    school = analysis.school or ""
    course = analysis.course or ""

    school_only_in_readme = bool(school and term_in_text(readme_text, school)) and not any(
        term_in_text(text, school) for text in (title_text, description_text, root_text)
    )
    course_aliases = get_course_aliases(course)
    course_only_in_readme = bool(course_aliases) and any(term_in_text(readme_text, alias) for alias in course_aliases) and not any(
        term_in_text(" ".join((title_text, description_text, root_text)), alias) for alias in course_aliases
    )
    root_paths = _root_paths(metadata)
    root_is_minimal = (not root_paths) or root_paths == ["README.md"] or _root_file_names(metadata) == ["README.md"]
    return root_is_minimal and (school_only_in_readme or course_only_in_readme)


def compute_penalty_score(evidence: EvidenceBundle, query_context: QueryAnalysis) -> float:
    penalty = 0.0
    query_intent = classify_query_intent(query_context)

    if evidence.repo_type == REPO_TYPE_ORG_META:
        penalty += 0.14
        evidence.negative_evidence.append("organization profile repo is not a concrete course project")
    if evidence.repo_type == REPO_TYPE_COLLECTION and query_intent != INTENT_COLLECTION:
        penalty += 0.08
        evidence.negative_evidence.append("multi-course collection is weaker than a targeted single-course repo")
    if evidence.repo_type == REPO_TYPE_EXAM_SOLUTION and query_intent in {INTENT_LAB, INTENT_PROJECT, INTENT_NOTES}:
        penalty += 0.10
        evidence.negative_evidence.append("exam/solution repo is not ideal for project/lab/notes intent")
    if evidence.repo_type == REPO_TYPE_GENERIC_ALGORITHM and evidence.school_match_strength != "strong":
        penalty += 0.10
        evidence.negative_evidence.append("generic algorithm repo lacks targeted school/course grounding")
    if evidence.school_match_strength == "none" and _target_school_profile(query_context) is not None:
        penalty += 0.08
        evidence.negative_evidence.append("candidate lacks target school evidence")
    if is_broad_school_scope(query_context.school_scope) and evidence.school_match_strength == "none":
        penalty += 0.10
        evidence.negative_evidence.append("candidate lacks concrete school evidence for the broad university scope")
    if evidence.school_group_match == "outside_scope":
        penalty += 0.08
        evidence.negative_evidence.append("detected school is outside the requested school group")
    if evidence.school_match_strength == "ambiguous":
        penalty += 0.06
        evidence.negative_evidence.append("school evidence relies on ambiguous abbreviation only")
    if evidence.course_negative_signals:
        penalty += 0.08
        evidence.negative_evidence.append(
            f"candidate also matches exam/solution-like course signals: {', '.join(evidence.course_negative_signals[:2])}"
        )
    if evidence.repo_type == REPO_TYPE_UNKNOWN:
        penalty += 0.04
    return _clamp(penalty)


def determine_score_cap(evidence: EvidenceBundle, query_context: QueryAnalysis) -> tuple[float, str | None]:
    query_intent = classify_query_intent(query_context)
    caps: list[tuple[str, float]] = []

    if evidence.repo_type == REPO_TYPE_ORG_META:
        caps.append(("org_meta_cap", SCORE_CAPS["org_meta_cap"]))
    if _target_school_profile(query_context) is not None:
        if evidence.school_match_strength == "none":
            caps.append(("school_none_cap", SCORE_CAPS["school_none_cap"]))
        elif evidence.school_match_strength == "weak":
            caps.append(("school_weak_cap", SCORE_CAPS["school_weak_cap"]))
        elif evidence.school_match_strength == "ambiguous":
            caps.append(("school_ambiguous_cap", SCORE_CAPS["school_ambiguous_cap"]))
    elif is_broad_school_scope(query_context.school_scope):
        if evidence.school_match_strength == "none":
            caps.append(("broad_scope_no_school_cap", SCORE_CAPS["broad_scope_no_school_cap"]))
        if evidence.school_group_match == "outside_scope":
            caps.append(("broad_scope_outside_group_cap", SCORE_CAPS["broad_scope_outside_group_cap"]))
        if evidence.school_match_strength == "ambiguous":
            caps.append(("school_ambiguous_cap", SCORE_CAPS["school_ambiguous_cap"]))
    if evidence.repo_type == REPO_TYPE_COLLECTION and query_intent != INTENT_COLLECTION:
        caps.append(("collection_cap", SCORE_CAPS["collection_cap"]))
    if evidence.repo_type == REPO_TYPE_EXAM_SOLUTION and query_intent in {INTENT_PROJECT, INTENT_LAB, INTENT_NOTES}:
        caps.append(("exam_solution_cap", SCORE_CAPS["exam_solution_cap"]))
    if evidence.repo_type == REPO_TYPE_GENERIC_ALGORITHM and evidence.school_match_strength != "strong":
        caps.append(("generic_algorithm_cap", SCORE_CAPS["generic_algorithm_cap"]))
    if evidence.course_negative_signals:
        caps.append(("course_negative_signal_cap", SCORE_CAPS["course_negative_signal_cap"]))

    if caps:
        reason_priority = [
            "org_meta_cap",
            "collection_cap",
            "exam_solution_cap",
            "generic_algorithm_cap",
            "course_negative_signal_cap",
            "readme_only_cap",
            "broad_scope_no_school_cap",
            "broad_scope_outside_group_cap",
            "school_none_cap",
            "school_ambiguous_cap",
            "school_weak_cap",
        ]
        cap_value = min(value for _, value in caps)
        chosen_reason = None
        for reason in reason_priority:
            if any(existing_reason == reason for existing_reason, _ in caps):
                chosen_reason = reason
                break
        return cap_value, chosen_reason
    return 1.0, None


def _value_level(final_score: float) -> str:
    if final_score >= VALUE_LEVEL_THRESHOLDS["high"]:
        return "high"
    if final_score >= VALUE_LEVEL_THRESHOLDS["medium"]:
        return "medium"
    return "low"


def _confidence_level(
    evidence: EvidenceBundle,
    score_breakdown: ScoreBreakdown,
) -> str:
    strong_count = 0
    if evidence.school_match_strength == "strong":
        strong_count += 1
    if evidence.course_score >= 0.85:
        strong_count += 1
    if evidence.intent_score >= 0.85 or evidence.structure_quality >= 0.80:
        strong_count += 1
    medium_count = sum(
        1
        for value in (
            evidence.course_score,
            evidence.intent_score,
            evidence.structure_quality,
            evidence.course_specificity,
        )
        if value >= 0.65
    )
    if strong_count >= 3:
        return "high"
    if strong_count >= 2 or (strong_count >= 1 and medium_count >= 3):
        return "medium"
    return "low"


def _apply_broad_scope_confidence_constraints(
    analysis: QueryAnalysis,
    evidence: EvidenceBundle,
    confidence: str,
) -> str:
    if not is_broad_school_scope(analysis.school_scope):
        return confidence

    adjusted = confidence
    if evidence.school_match_strength == "weak" and adjusted == "high":
        adjusted = "medium"
    if evidence.school_match_strength == "ambiguous":
        if adjusted == "high":
            adjusted = "medium"
        if adjusted == "medium" and evidence.course_score < 0.85:
            adjusted = "low"
    if evidence.school_match_strength == "none":
        if evidence.course_score >= 0.85 and (
            evidence.intent_score >= 0.85 or evidence.structure_quality >= 0.80
        ):
            adjusted = "medium"
        else:
            adjusted = "low"
    if evidence.school_group_match == "outside_scope":
        if adjusted == "high":
            adjusted = "medium"
        elif adjusted == "medium" and evidence.school_match_strength != "strong":
            adjusted = "low"
    return adjusted


def _why_recommended(
    analysis: QueryAnalysis,
    evidence: EvidenceBundle,
    *,
    detected_school: str | None,
    matched_course: str | None,
    matched_intent: str | None,
) -> str:
    parts: list[str] = []
    top_reasons = evidence.positive_evidence[:3]
    has_structure_support = evidence.structure_quality >= 0.70 or any(
        marker in safe_lower(reason)
        for reason in top_reasons
        for marker in ("root entries contain", "structure detected", "code and report coexist")
    )
    has_content_support = evidence.content_richness >= 0.65 or any(
        marker in safe_lower(reason)
        for reason in top_reasons
        for marker in ("readme includes", "readme explains", "readme contains", "readme repeatedly mentions")
    )
    if detected_school and evidence.school_match_strength in {"strong", "weak"}:
        parts.append(detected_school)
    if matched_course:
        parts.append(matched_course)
    if matched_intent:
        intent_label = {
            INTENT_LAB: "实验",
            INTENT_PROJECT: "课程项目",
            INTENT_NOTES: "笔记",
            INTENT_EXAM: "试题/题解",
            INTENT_COLLECTION: "资料合集",
        }.get(matched_intent, matched_intent)
        parts.append(intent_label)

    if parts:
        prefix = "、".join(parts[:3])
        if has_structure_support:
            return f"命中{prefix}，且仓库描述和目录结构均支持当前课程项目判断。"
        if has_content_support:
            return f"命中{prefix}，且 README/仓库描述提供了较完整的课程背景说明。"
        return f"命中{prefix}，可作为课程项目调研和学习参考入口。"

    if evidence.positive_evidence:
        return f"推荐依据：{'；'.join(evidence.positive_evidence[:3])}。"
    return "可作为公开课程资料线索，但仍需人工核验内容质量。"


def _classify_item(item: ProviderSearchResult) -> tuple[str, dict[str, Any], list[str], list[str]]:
    metadata = dict(item.metadata or {})
    description = " ".join(
        part for part in [str(metadata.get("description") or ""), item.snippet or ""] if part
    )
    classification = classify_repository(
        title=item.title or "",
        description=description,
        readme_text=_readme_text(metadata),
        metadata=metadata,
    )
    return (
        classification.repo_type,
        classification.signals,
        list(classification.positive_evidence),
        list(classification.negative_evidence),
    )


def explain_score(analysis: QueryAnalysis, item: ProviderSearchResult) -> ScoreExplanation:
    metadata = dict(item.metadata or {})
    repo_type, repo_signals, classifier_positive, classifier_negative = _classify_item(item)

    positive_evidence = list(classifier_positive)
    negative_evidence = list(classifier_negative)
    course_profile = _course_profile_for_item(analysis, item)
    course_specific_assets = _course_specific_assets_for_item(course_profile, item)
    course_negative_signals = course_negative_signal_hits(
        course_profile,
        _joined_candidate_text(item),
        limit=3,
    ) if course_profile is not None else []

    target_match, detected_match = _select_best_school_match(analysis, item)
    school_score, school_strength, school_evidence, school_aliases, matched_school, detected_school = _compute_school_score(
        analysis,
        target_match,
        detected_match,
    )
    school_group_match = _scope_group_match(analysis, detected_match)
    if school_evidence:
        positive_evidence.extend(school_evidence[:3])

    course_score, matched_course = _compute_course_score(
        analysis,
        item,
        positive_evidence,
        course_profile=course_profile,
        course_specific_assets=course_specific_assets,
    )
    intent_score, matched_intent = _compute_intent_score(
        analysis,
        repo_type,
        {**repo_signals, **_root_signal(metadata)},
        positive_evidence,
    )
    keyword_score = _compute_keyword_score(analysis, item, positive_evidence)

    platform_trust = resolve_platform_trust(_source_provider(item))
    domain_trust = resolve_domain_trust(item.url)
    content_richness = compute_content_richness(item)
    structure_quality = _compute_structure_quality(
        item,
        analysis,
        course_profile=course_profile,
        course_specific_assets=course_specific_assets,
    )
    course_specificity = _compute_course_specificity(
        item,
        analysis,
        course_profile=course_profile,
        course_specific_assets=course_specific_assets,
    )
    reference_utility_score, reference_utility = _compute_reference_utility(
        item,
        analysis,
        course_profile=course_profile,
        course_specific_assets=course_specific_assets,
    )
    repo_health = compute_repo_health(item)
    freshness_score = _compute_freshness_score(item)
    popularity_score = _compute_popularity_score(item, positive_evidence)

    evidence = EvidenceBundle(
        school_score=_round_score(school_score),
        course_score=_round_score(course_score),
        intent_score=_round_score(intent_score),
        keyword_score=_round_score(keyword_score),
        platform_trust=_round_score(platform_trust),
        domain_trust=_round_score(domain_trust),
        content_richness=_round_score(content_richness),
        structure_quality=_round_score(structure_quality),
        course_specificity=_round_score(course_specificity),
        repo_health=_round_score(repo_health),
        reference_utility_score=_round_score(reference_utility_score),
        freshness_score=_round_score(freshness_score),
        popularity_score=_round_score(popularity_score),
        school_match_strength=school_strength,
        school_group_match=school_group_match,
        repo_type=repo_type,
        course_profile_id=course_profile.id if course_profile is not None else None,
        course_specific_assets=course_specific_assets,
        course_negative_signals=course_negative_signals,
        positive_evidence=unique_preserve_order(positive_evidence),
        negative_evidence=unique_preserve_order(negative_evidence),
        reference_utility=reference_utility,
    )

    if _readme_only_weak_match(analysis, item):
        evidence.negative_evidence.append("match relies on README only without metadata/root support")

    if metadata.get("enrichment_failed"):
        evidence.negative_evidence.append("github enrichment failed; content/structure evidence is incomplete")

    evidence.penalty_score = _round_score(compute_penalty_score(evidence, analysis))
    cap, cap_reason = determine_score_cap(evidence, analysis)
    if _readme_only_weak_match(analysis, item):
        cap = min(cap, SCORE_CAPS["readme_only_cap"])
        cap_reason = "readme_only_cap" if cap == SCORE_CAPS["readme_only_cap"] else cap_reason
    if metadata.get("archived"):
        archived_cap = SCORE_CAPS["archived_cap"]
        if archived_cap < cap:
            cap = archived_cap
            cap_reason = "archived_cap"
        evidence.negative_evidence.append("repository is archived")
    evidence.cap = _round_score(cap)
    evidence.cap_reason = cap_reason

    relevance_score = sum(
        getattr(evidence, key) * weight for key, weight in RELEVANCE_WEIGHTS.items()
    )
    source_value_score = sum(
        getattr(evidence, key) * weight for key, weight in SOURCE_VALUE_WEIGHTS.items()
    )
    freshness_popularity_score = sum(
        getattr(evidence, key) * weight for key, weight in FRESHNESS_POPULARITY_WEIGHTS.items()
    )
    strong_bonus = _strong_alignment_bonus(evidence, metadata)
    raw_score = (
        RAW_SCORE_WEIGHTS["relevance_score"] * relevance_score
        + RAW_SCORE_WEIGHTS["source_value_score"] * source_value_score
        + RAW_SCORE_WEIGHTS["freshness_popularity_score"] * freshness_popularity_score
        + strong_bonus
        - evidence.penalty_score
    )
    raw_score = _clamp(raw_score)
    final_score = _round_score(min(raw_score, evidence.cap))

    structure_evidence = _collect_structure_positive_evidence(
        metadata,
        query_intent=classify_query_intent(analysis),
    )
    content_evidence = _collect_content_positive_evidence(metadata)
    evidence.positive_evidence = _sort_positive_evidence(
        [
            *evidence.positive_evidence,
            *structure_evidence,
            *content_evidence,
        ],
        school_evidence=school_evidence,
        matched_school_aliases=school_aliases,
        matched_course=matched_course,
    )
    evidence.positive_evidence = _limit_positive_evidence(
        evidence.positive_evidence,
        school_evidence=school_evidence,
        matched_school_aliases=school_aliases,
        matched_course=matched_course,
        limit=POSITIVE_EVIDENCE_LIMIT,
    )
    evidence.negative_evidence = _sort_negative_evidence(evidence.negative_evidence)[:NEGATIVE_EVIDENCE_LIMIT]

    breakdown = ScoreBreakdown(
        relevance_score=_round_score(relevance_score),
        source_value_score=_round_score(source_value_score),
        freshness_popularity_score=_round_score(freshness_popularity_score),
        raw_score=_round_score(raw_score),
        final_score=final_score,
        value_level=_value_level(final_score),
        cap_reason=cap_reason,
    )
    breakdown.confidence = _confidence_level(evidence, breakdown)
    breakdown.confidence = _apply_broad_scope_confidence_constraints(
        analysis,
        evidence,
        breakdown.confidence,
    )

    detected_school_id = detected_match.profile.id if detected_match and detected_match.matched_aliases else None
    why_recommended = _why_recommended(
        analysis,
        evidence,
        detected_school=detected_school,
        matched_course=matched_course,
        matched_intent=matched_intent,
    )

    return ScoreExplanation(
        evidence_bundle=evidence,
        score_breakdown=breakdown,
        matched_school=matched_school,
        detected_school=detected_school,
        detected_school_id=detected_school_id,
        school_evidence=school_evidence,
        matched_school_aliases=school_aliases,
        matched_course=matched_course,
        matched_intent=matched_intent,
        query_intent=classify_query_intent(analysis),
        candidate_intents=[REPO_TYPE_TO_INTENT.get(repo_type, INTENT_GENERIC)],
        source_provider=_source_provider(item),
        why_recommended=why_recommended,
        reasons=unique_preserve_order([*evidence.positive_evidence, *evidence.negative_evidence])[:6],
        caveat=DEFAULT_CAVEAT,
    )


def score_provider_result(analysis: QueryAnalysis, item: ProviderSearchResult) -> tuple[float, str]:
    explanation = explain_score(analysis, item)
    summary = explanation.summary()
    if "public visibility" not in summary:
        visibility_reason = next(
            (reason for reason in explanation.positive_evidence if "public visibility" in reason),
            None,
        )
        if visibility_reason:
            summary = f"{summary}; {visibility_reason}" if summary else visibility_reason
    return explanation.final_score, summary
