from __future__ import annotations

import re

from app.core.course_profiles import detect_courses, get_course_profile
from app.core.university_profiles import (
    UniversityMatch,
    detect_school_scope,
    detect_university_matches,
    get_university_profile,
)
from app.core.vocabulary import (
    find_computing_topics,
    find_course,
    find_info_scope_keywords,
    find_project_keywords,
    find_resource_keywords,
    find_source_type_hints,
    find_tech_keywords,
)
from app.schemas import QueryAnalysis
from app.utils.text import guess_year, safe_lower, unique_preserve_order

"""
这个文件负责把自然语言查询拆成结构化分析结果。
后面的 provider 选择、搜索词构造和排序规则，都会依赖这里给出的 school/course/intent 线索。
"""


def _merge_school_matches(
    explicit_match: UniversityMatch | None,
    detected_matches: list[UniversityMatch],
) -> list[UniversityMatch]:
    merged: list[UniversityMatch] = []
    seen_ids: set[str] = set()

    for match in [explicit_match, *detected_matches]:
        if match is None or match.profile.id in seen_ids:
            continue
        seen_ids.add(match.profile.id)
        merged.append(match)
    return merged


def analyze_query(
    query: str,
    *,
    school: str | None = None,
    course: str | None = None,
    source_types: list[str] | None = None,
) -> QueryAnalysis:
    raw = query or ""
    explicit_course_profile = get_course_profile(course) if course else None
    detected_course_profiles = detect_courses(raw)

    explicit_profile = get_university_profile(school)
    detected_matches = detect_university_matches(raw)
    explicit_match: UniversityMatch | None = None
    if explicit_profile and school:
        explicit_match = UniversityMatch(
            profile=explicit_profile,
            matched_aliases=[school],
            ambiguous_aliases=[school]
            if safe_lower(school) in explicit_profile.ambiguous_alias_set()
            else [],
            evidence=[f"explicit school input `{school}`"],
            has_canonical_name=school == explicit_profile.canonical_name,
            has_english_name=school == explicit_profile.english_name,
        )

    school_matches = _merge_school_matches(explicit_match, detected_matches)
    detected_school = None
    detected_school_id = None
    if explicit_profile:
        detected_school = explicit_profile.canonical_name
        detected_school_id = explicit_profile.id
    elif school:
        detected_school = school
    elif len(school_matches) == 1:
        detected_school = school_matches[0].profile.canonical_name
        detected_school_id = school_matches[0].profile.id

    detected_course = None
    detected_course_profile_id = None
    if explicit_course_profile is not None:
        detected_course = explicit_course_profile.canonical_name
        detected_course_profile_id = explicit_course_profile.id
    elif course:
        detected_course = course
    elif detected_course_profiles:
        detected_course = detected_course_profiles[0].canonical_name
        detected_course_profile_id = detected_course_profiles[0].id
    detected_year = guess_year(raw)

    project_keywords = find_project_keywords(raw)
    tech_keywords = find_tech_keywords(raw)
    resource_keywords = unique_preserve_order(
        [
            *find_resource_keywords(raw),
            *find_info_scope_keywords(raw),
            *(
                []
                if explicit_course_profile is not None or detected_course_profiles
                else find_computing_topics(raw)
            ),
        ]
    )

    detected_source_types = list(source_types or [])
    source_type_reasons: list[str] = []
    if not detected_source_types:
        source_hints = find_source_type_hints(raw)
        detected_source_types = [source_type for source_type, _ in source_hints]
        source_type_reasons = [
            f"{source_type}: query hint `{hint}`" for source_type, hint in source_hints
        ]
    else:
        source_type_reasons = [f"{source_type}: explicit input" for source_type in detected_source_types]

    school_scope = detect_school_scope(raw, matches=school_matches)
    if school and not explicit_profile and school_scope.kind == "none":
        school_scope.evidence = ["explicit school input"]

    return QueryAnalysis(
        raw_query=raw,
        school=detected_school,
        school_id=detected_school_id,
        detected_schools=[match.profile.canonical_name for match in school_matches],
        detected_school_ids=[match.profile.id for match in school_matches],
        school_detection=[match.as_dict() for match in school_matches],
        school_scope=school_scope.kind,
        scope_evidence=school_scope.evidence,
        course=detected_course,
        course_profile_id=detected_course_profile_id,
        detected_courses=unique_preserve_order(
            [
                *([explicit_course_profile.canonical_name] if explicit_course_profile is not None else []),
                *[profile.canonical_name for profile in detected_course_profiles],
            ]
        ),
        detected_course_ids=unique_preserve_order(
            [
                *([explicit_course_profile.id] if explicit_course_profile is not None else []),
                *[profile.id for profile in detected_course_profiles],
            ]
        ),
        project_keywords=project_keywords,
        tech_keywords=tech_keywords,
        resource_keywords=resource_keywords,
        year_hint=detected_year,
        source_types=unique_preserve_order(detected_source_types),
        source_type_reasons=source_type_reasons,
    )


def build_search_query(analysis: QueryAnalysis) -> str:
    # 搜索词的目标不是“还原原句”，而是抽出最能提高命中率的几个关键词。
    parts: list[str] = []
    blocked_resource_terms = {
        "repository",
        "blog",
        "lab_material",
        "slides_or_report",
        "tutorial",
    }

    if analysis.school:
        parts.append(analysis.school)
    if analysis.course:
        parts.append(analysis.course)

    parts.extend(analysis.project_keywords[:3])
    parts.extend(analysis.tech_keywords[:4])
    parts.extend(
        [
            keyword
            for keyword in analysis.resource_keywords
            if safe_lower(keyword) not in blocked_resource_terms
        ][:2]
    )

    if analysis.year_hint:
        parts.append(str(analysis.year_hint))

    if not parts:
        return analysis.raw_query.strip()

    compact = " ".join(unique_preserve_order(parts)).strip()
    return re.sub(r"\s+", " ", compact)
