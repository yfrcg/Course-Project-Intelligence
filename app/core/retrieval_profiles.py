from __future__ import annotations

from app.core.course_profiles import (
    get_course_profile,
    pick_course_intent_keywords,
    pick_course_query_aliases,
    pick_course_structure_terms,
)
from app.core.query_analyzer import build_search_query
from app.core.retrieval_intents import (
    INTENT_COLLECTION,
    INTENT_EXAM,
    INTENT_LAB,
    INTENT_NOTES,
    INTENT_PROJECT,
    INTENT_SOLUTION,
    classify_query_intent,
)
from app.core.university_profiles import (
    UniversityProfile,
    get_university_profile,
    school_query_terms,
)
from app.core.vocabulary import (
    find_computing_topics,
    find_info_scope_keywords,
    get_course_aliases,
    get_school_aliases,
    term_in_text,
)
from app.schemas import QueryAnalysis
from app.utils.text import extract_keywords, safe_lower, unique_preserve_order

"""
这个文件负责把 query analysis 继续扩成可执行的检索策略。
例如：什么时候引入院系官网种子页，什么时候扩 GitHub query，都是在这里决定。
"""


def _target_school_profiles(analysis: QueryAnalysis) -> list[UniversityProfile]:
    profiles: list[UniversityProfile] = []
    seen: set[str] = set()
    for school_id in analysis.detected_school_ids:
        profile = get_university_profile(school_id)
        if profile is None or profile.id in seen:
            continue
        seen.add(profile.id)
        profiles.append(profile)
    if not profiles and analysis.school_id:
        profile = get_university_profile(analysis.school_id)
        if profile is not None:
            profiles.append(profile)
    return profiles


def is_nankai_computer_query(analysis: QueryAnalysis) -> bool:
    if analysis.school_id != "nankai":
        return False

    profile = get_university_profile("nankai")
    if profile is None:
        return False

    if analysis.course:
        return True

    text = " ".join(
        [
            analysis.raw_query or "",
            " ".join(analysis.project_keywords),
            " ".join(analysis.tech_keywords),
            " ".join(analysis.resource_keywords),
        ]
    )

    if any(term_in_text(text, term) for term in profile.computer_context_terms):
        return True

    return bool(find_computing_topics(text))


def build_relevance_terms(analysis: QueryAnalysis) -> list[str]:
    terms: list[str] = []
    course_profile = get_course_profile(analysis.course_profile_id or analysis.course)

    if analysis.detected_schools:
        for school_name in analysis.detected_schools:
            terms.extend(get_school_aliases(school_name))
    else:
        terms.extend(get_school_aliases(analysis.school))
    terms.extend(get_course_aliases(analysis.course))
    if course_profile is not None:
        terms.extend(course_profile.structure_signals[:3])
        terms.extend(course_profile.reference_criteria[:2])
    terms.extend(analysis.project_keywords[:6])
    terms.extend(analysis.tech_keywords[:6])
    terms.extend(analysis.resource_keywords[:6])
    terms.extend(find_computing_topics(analysis.raw_query))
    terms.extend(find_info_scope_keywords(analysis.raw_query))
    terms.extend(extract_keywords(analysis.raw_query, top_k=8))

    if is_nankai_computer_query(analysis):
        profile = get_university_profile("nankai")
        if profile is not None:
            terms.extend(profile.computer_expansion_terms)

    return unique_preserve_order(terms)


def build_seed_sites(analysis: QueryAnalysis, default_seeds: list[str]) -> list[str]:
    seeds: list[str] = []

    if is_nankai_computer_query(analysis):
        profile = get_university_profile("nankai")
        if profile is not None:
            text = analysis.raw_query or ""
            matched_intents = [
                intent
                for intent, keywords in profile.computer_ecosystem_intent_keywords.items()
                if any(term_in_text(text, keyword) for keyword in keywords)
            ]
            if profile.computer_ecosystem_seeds.get("overview"):
                seeds.append(profile.computer_ecosystem_seeds["overview"])
            for intent in matched_intents:
                if profile.computer_ecosystem_seeds.get(intent):
                    seeds.append(profile.computer_ecosystem_seeds[intent])
            for intent in profile.computer_ecosystem_intent_order:
                if profile.computer_ecosystem_seeds.get(intent):
                    seeds.append(profile.computer_ecosystem_seeds[intent])

    seeds.extend(default_seeds)
    return unique_preserve_order(seeds)


def _quote_search_term(term: str) -> str:
    cleaned = " ".join((term or "").replace('"', " ").split()).strip()
    if not cleaned:
        return ""
    if " " in cleaned:
        return f'"{cleaned}"'
    return cleaned


def _append_github_qualifiers(
    query: str,
    *,
    search_in: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    include_forks: bool = False,
    pushed_since_year: int | None = None,
) -> str:
    parts = [" ".join(query.split()).strip()]

    if search_in:
        parts.append(f"in:{search_in}")
    if topic:
        parts.append(f"topic:{topic}")
    if language:
        parts.append(f"language:{language}")

    parts.append("archived:false")

    if include_forks:
        parts.append("fork:true")
    if pushed_since_year:
        parts.append(f"pushed:>={pushed_since_year}-01-01")

    return " ".join(part for part in parts if part).strip()


def _compose_github_query(
    terms: list[str],
    *,
    search_in: str | None = None,
    topic: str | None = None,
    language: str | None = None,
    include_forks: bool = False,
    pushed_since_year: int | None = None,
) -> str:
    query = " ".join(
        _quote_search_term(term)
        for term in unique_preserve_order(terms)
        if _quote_search_term(term)
    )
    return _append_github_qualifiers(
        query,
        search_in=search_in,
        topic=topic,
        language=language,
        include_forks=include_forks,
        pushed_since_year=pushed_since_year,
    )


def _pick_course_aliases_for_github(canonical: str | None) -> list[str]:
    profile = get_course_profile(canonical)
    alias_groups = pick_course_query_aliases(profile)
    aliases = unique_preserve_order(
        [
            *alias_groups["canonical"],
            *alias_groups["english"],
            *alias_groups["short"],
            *alias_groups["fallback"],
        ]
    )
    if not aliases:
        aliases = get_course_aliases(canonical)
    if not aliases:
        return []

    preferred: list[str] = [aliases[0]]
    english_aliases = [alias for alias in aliases if alias.isascii() and len(alias) > 4]
    short_aliases = [alias for alias in aliases if alias.isascii() and len(alias) <= 4]
    preferred.extend(english_aliases[:1])
    preferred.extend(short_aliases[:1])
    preferred.extend(aliases)
    return unique_preserve_order(preferred)[:4]


def _pick_school_terms_for_github(profile: UniversityProfile) -> dict[str, list[str]]:
    term_groups = school_query_terms(profile)
    return {
        "canonical": term_groups["canonical"][:1],
        "abbreviation": term_groups["abbreviation"][:2],
        "english": term_groups["english"][:1],
        "fallback": term_groups["fallback"][:2],
    }


def is_github_note_query(analysis: QueryAnalysis) -> bool:
    return classify_query_intent(analysis) == INTENT_NOTES


def is_github_project_query(analysis: QueryAnalysis) -> bool:
    return classify_query_intent(analysis) in {INTENT_PROJECT, INTENT_LAB}


def is_github_exam_query(analysis: QueryAnalysis) -> bool:
    return classify_query_intent(analysis) == INTENT_EXAM


def build_github_intent_terms(analysis: QueryAnalysis) -> list[str]:
    intent = classify_query_intent(analysis)
    terms: list[str] = []

    if intent == INTENT_NOTES:
        terms.extend(["notes", "笔记", "lecture notes", "markdown", "obsidian"])
    elif intent == INTENT_PROJECT:
        terms.extend(["大作业", "course project", "final project", "课程设计"])
    elif intent == INTENT_LAB:
        terms.extend(["lab", "labs", "实验", "实验报告"])
    elif intent == INTENT_EXAM:
        terms.extend(["exam", "exams", "试题", "期末"])
    elif intent == INTENT_SOLUTION:
        terms.extend(["solution", "answer", "答案", "题解"])
    elif intent == INTENT_COLLECTION:
        terms.extend(["courses", "resources", "课程资料", "合集"])

    if not terms:
        terms.extend(analysis.project_keywords[:2])
        terms.extend(analysis.resource_keywords[:2])

    return unique_preserve_order(terms)


def _build_school_specific_github_queries(
    profile: UniversityProfile,
    course_aliases: list[str],
    intent_terms: list[str],
    course_structure_terms: list[str],
    scope_terms: list[str],
    pushed_since_year: int | None,
    *,
    query_intent: str,
) -> tuple[list[str], list[str]]:
    school_terms = _pick_school_terms_for_github(profile)
    canonical_school = school_terms["canonical"][:1]
    abbreviation_school = school_terms["abbreviation"][:1]
    english_school = school_terms["english"][:1]
    fallback_school = school_terms["fallback"][:1]

    primary_course = course_aliases[:1]
    english_course = [alias for alias in course_aliases if alias.isascii() and len(alias) > 4][:1]
    fallback_course = course_aliases[1:2] or primary_course
    primary_intent = intent_terms[:1]

    precision_queries: list[str] = []
    fallback_queries: list[str] = []

    if canonical_school and primary_course:
        precision_queries.append(
            _compose_github_query(
                [*canonical_school, *primary_course, *primary_intent, *course_structure_terms[:1], *scope_terms],
                search_in="name,description,readme",
                pushed_since_year=pushed_since_year,
            )
        )
        precision_queries.append(
            _compose_github_query(
                [*canonical_school, *primary_course],
                search_in="readme",
                pushed_since_year=pushed_since_year,
            )
        )

    if abbreviation_school and primary_course:
        precision_queries.append(
            _compose_github_query(
                [
                    *abbreviation_school,
                    *(english_course or primary_course),
                    *primary_intent,
                    *course_structure_terms[:1],
                ],
                search_in="name,description,readme",
                pushed_since_year=pushed_since_year,
            )
        )

    if english_school and primary_course:
        precision_queries.append(
            _compose_github_query(
                [
                    *english_school,
                    *(english_course or primary_course),
                    *primary_intent,
                    *course_structure_terms[:1],
                ],
                search_in="name,description,readme",
                pushed_since_year=pushed_since_year,
            )
        )

    if fallback_school and primary_course:
        fallback_queries.append(
            _compose_github_query(
                [
                    *fallback_school,
                    *(fallback_course or primary_course),
                    *primary_intent,
                    *course_structure_terms[:1],
                ],
                search_in="name,description,readme",
                include_forks=True,
                pushed_since_year=pushed_since_year,
            )
        )

    if query_intent == INTENT_NOTES and canonical_school and primary_course:
        fallback_queries.append(
            _compose_github_query(
                [*canonical_school, *primary_course, "notes"],
                search_in="name,description,readme",
                language="Markdown",
                pushed_since_year=pushed_since_year,
            )
        )
        fallback_queries.append(
            _compose_github_query(
                [*canonical_school, *primary_course],
                topic="notes",
                pushed_since_year=pushed_since_year,
            )
        )

    if query_intent in {INTENT_PROJECT, INTENT_LAB} and canonical_school and primary_course:
        fallback_queries.append(
            _compose_github_query(
                [*canonical_school, *primary_course, *course_structure_terms[:1]],
                topic="course-project",
                pushed_since_year=pushed_since_year,
            )
        )
        fallback_queries.append(
            _compose_github_query(
                [*(abbreviation_school or canonical_school), *primary_course, *course_structure_terms[:1]],
                topic="lab",
                pushed_since_year=pushed_since_year,
            )
        )

    if canonical_school and primary_course and course_structure_terms:
        fallback_queries.append(
            _compose_github_query(
                [*canonical_school, *(course_aliases[:1] or primary_course), *course_structure_terms[:1]],
                search_in="name,description,readme",
                pushed_since_year=pushed_since_year,
            )
        )

    return precision_queries, fallback_queries


def build_github_search_queries(analysis: QueryAnalysis) -> list[str]:
    base_query = build_search_query(analysis).strip()
    raw_query = (analysis.raw_query or "").strip()
    pushed_since_year = analysis.year_hint
    precision_queries: list[str] = []
    fallback_queries: list[str] = []
    query_intent = classify_query_intent(analysis)
    course_profile = get_course_profile(analysis.course_profile_id or analysis.course)

    for query in [base_query, raw_query]:
        if not query:
            continue
        precision_queries.append(
            _append_github_qualifiers(
                query,
                search_in="name,description,readme",
                pushed_since_year=pushed_since_year,
            )
        )
        precision_queries.append(
            _append_github_qualifiers(
                query,
                search_in="readme",
                pushed_since_year=pushed_since_year,
            )
        )

    course_aliases = _pick_course_aliases_for_github(analysis.course)
    intent_terms = unique_preserve_order(
        [
            *pick_course_intent_keywords(course_profile, query_intent),
            *build_github_intent_terms(analysis),
        ]
    )[:2]
    course_structure_terms = unique_preserve_order(
        [
            *pick_course_structure_terms(course_profile, query_intent),
            *analysis.tech_keywords[:1],
        ]
    )[:2]
    scope_terms = find_info_scope_keywords(analysis.raw_query)[:2]
    target_profiles = _target_school_profiles(analysis)

    if target_profiles and course_aliases:
        for profile in target_profiles[:3]:
            school_precision, school_fallback = _build_school_specific_github_queries(
                profile,
                course_aliases,
                intent_terms,
                course_structure_terms,
                scope_terms,
                pushed_since_year,
                query_intent=query_intent,
            )
            precision_queries.extend(school_precision)
            fallback_queries.extend(school_fallback)

    if is_nankai_computer_query(analysis):
        profile = get_university_profile("nankai")
        if profile is not None:
            fallback_queries.extend(
                [
                    _compose_github_query(
                        [profile.canonical_name, "计算机学院", *intent_terms[:1]],
                        search_in="name,description,readme",
                        pushed_since_year=pushed_since_year,
                    ),
                    _compose_github_query(
                        [profile.canonical_name, "计算机科学与技术", *intent_terms[:1]],
                        search_in="readme",
                        pushed_since_year=pushed_since_year,
                    ),
                    _compose_github_query(
                        ["nankai", "computer science", *intent_terms[:1]],
                        search_in="name,description,readme",
                        pushed_since_year=pushed_since_year,
                    ),
                    _compose_github_query(
                        ["nku", "computer science", *intent_terms[:1]],
                        search_in="name,description,readme",
                        pushed_since_year=pushed_since_year,
                    ),
                ]
            )

    if course_aliases:
        fallback_queries.append(
            _compose_github_query(
                [course_aliases[0], *intent_terms[:1], *course_structure_terms[:1], *scope_terms[:1]],
                search_in="name,description,readme",
                pushed_since_year=pushed_since_year,
            )
        )
        if len(course_aliases) >= 2:
            fallback_queries.append(
                _compose_github_query(
                    [course_aliases[1], *intent_terms[:1], *course_structure_terms[:1]],
                    search_in="readme",
                    pushed_since_year=pushed_since_year,
                )
            )

    for query in [base_query, raw_query]:
        if not query:
            continue
        fallback_queries.append(
            _append_github_qualifiers(
                query,
                search_in="name,description,readme",
                include_forks=True,
                pushed_since_year=pushed_since_year,
            )
        )

    if target_profiles and course_aliases:
        primary_profile = target_profiles[0]
        primary_terms = _pick_school_terms_for_github(primary_profile)
        fallback_queries.append(
            _compose_github_query(
                [
                    primary_terms["canonical"][0],
                    course_aliases[0],
                    *intent_terms[:1],
                    *course_structure_terms[:1],
                ],
                search_in="name,description,readme",
                include_forks=True,
                pushed_since_year=pushed_since_year,
            )
        )

    queries = [*precision_queries, *fallback_queries]
    return unique_preserve_order([query.strip() for query in queries if query.strip()])
