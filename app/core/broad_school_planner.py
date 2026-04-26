from __future__ import annotations

from dataclasses import dataclass, field

from app.core.course_profiles import (
    get_course_profile,
    pick_course_intent_keywords,
    pick_course_structure_terms,
)
from app.core.query_analyzer import analyze_query
from app.core.retrieval_intents import INTENT_GENERIC, classify_query_intent, intent_terms
from app.core.university_profiles import (
    BROAD_SCHOOL_SCOPE_KINDS,
    UniversityProfile,
    group_for_school_scope,
    is_broad_school_scope,
    list_university_profiles,
    list_university_profiles_by_group,
)
from app.core.vocabulary import term_in_text
from app.schemas import QueryAnalysis
from app.utils.text import unique_preserve_order


DEFAULT_MAX_SCHOOLS_PER_BROAD_QUERY = 10
DEFAULT_PER_SCHOOL_CANDIDATE_BUDGET = 2
DEFAULT_MAX_TOTAL_CANDIDATES = 30
DEFAULT_MAX_RESULTS_PER_SCHOOL_IN_TOP = 2


@dataclass(frozen=True)
class BroadSchoolPlannerConfig:
    max_schools_per_broad_query: int = DEFAULT_MAX_SCHOOLS_PER_BROAD_QUERY
    per_school_candidate_budget: int = DEFAULT_PER_SCHOOL_CANDIDATE_BUDGET
    max_total_candidates: int = DEFAULT_MAX_TOTAL_CANDIDATES
    max_results_per_school_in_top: int = DEFAULT_MAX_RESULTS_PER_SCHOOL_IN_TOP


@dataclass
class PlannedSchoolQuery:
    profile: UniversityProfile
    query: str
    analysis: QueryAnalysis
    candidate_budget: int


@dataclass
class BroadSchoolPlan:
    scope_kind: str
    school_group: str | None
    scope_note: str
    profiles_considered: list[UniversityProfile] = field(default_factory=list)
    school_queries: list[PlannedSchoolQuery] = field(default_factory=list)
    per_school_candidate_budget: int = DEFAULT_PER_SCHOOL_CANDIDATE_BUDGET
    max_total_candidates: int = DEFAULT_MAX_TOTAL_CANDIDATES
    max_results_per_school_in_top: int = DEFAULT_MAX_RESULTS_PER_SCHOOL_IN_TOP

    @property
    def profile_count(self) -> int:
        return len(self.profiles_considered)


def _target_profiles_for_scope(scope_kind: str) -> list[UniversityProfile]:
    group = group_for_school_scope(scope_kind)
    if group:
        return list_university_profiles_by_group(group)
    return list_university_profiles()


def _school_limit_for_request(requested_top_k: int, config: BroadSchoolPlannerConfig) -> int:
    dynamic_limit = max(4, min(config.max_schools_per_broad_query, requested_top_k * 2))
    return max(1, dynamic_limit)


def _filtered_scope_keywords(base_analysis: QueryAnalysis) -> list[str]:
    scope_noise_terms = {
        "project_985": {"985"},
        "project_211": {"211"},
        "c9": {"c9", "九校联盟"},
        "double_first_class": {"双一流", "double first class"},
    }
    blocked_terms = scope_noise_terms.get(base_analysis.school_scope, set())
    return [
        keyword
        for keyword in base_analysis.project_keywords
        if keyword and keyword.lower() not in blocked_terms
    ]


def _intent_hint_terms(base_analysis: QueryAnalysis) -> list[str]:
    detected_intent = classify_query_intent(base_analysis)
    if detected_intent == INTENT_GENERIC:
        return []

    matched_terms = [
        term for term in intent_terms(detected_intent) if term and term_in_text(base_analysis.raw_query, term)
    ]
    if matched_terms:
        return unique_preserve_order(matched_terms[:2])

    fallback_terms = {
        "notes": ["笔记", "notes"],
        "project": ["大作业", "project"],
        "lab": ["实验", "lab"],
        "exam": ["试题", "exam"],
        "solution": ["题解", "solution"],
        "collection": ["资料合集", "courses"],
    }
    return fallback_terms.get(detected_intent, [])[:2]


def _build_school_specific_query(base_analysis: QueryAnalysis, profile: UniversityProfile) -> str:
    query_intent = classify_query_intent(base_analysis)
    course_profile = get_course_profile(base_analysis.course_profile_id or base_analysis.course)
    course_intent_terms = pick_course_intent_keywords(course_profile, query_intent)
    course_structure_terms = pick_course_structure_terms(course_profile, query_intent)

    parts: list[str] = [profile.canonical_name]
    if base_analysis.course:
        parts.append(base_analysis.course)
    parts.extend(unique_preserve_order([*course_intent_terms, *_intent_hint_terms(base_analysis)])[:2])
    parts.extend(course_structure_terms[:1])
    parts.extend(_filtered_scope_keywords(base_analysis)[:2])
    parts.extend(base_analysis.tech_keywords[:2])
    parts.extend(base_analysis.resource_keywords[:1])
    if "github" in {source_type.lower() for source_type in base_analysis.source_types}:
        parts.append("github")
    if base_analysis.year_hint:
        parts.append(str(base_analysis.year_hint))
    return " ".join(unique_preserve_order([part for part in parts if part])).strip()


def _scope_note(scope_kind: str, school_group: str | None) -> str:
    if scope_kind == "broad_university":
        return (
            "已在首批高校 profile 中进行分批召回，结果按学校证据、课程证据、实验/项目类型、"
            "仓库结构和信源价值统一排序；当前不保证覆盖全部高校。"
        )
    group_label = school_group or scope_kind
    return (
        f"已在首批 {group_label} 高校 profile 中进行分批召回，结果按学校证据、课程证据、实验/项目类型、"
        "仓库结构和信源价值统一排序；当前不保证覆盖该范围内全部高校。"
    )


def plan_broad_school_retrieval(
    base_analysis: QueryAnalysis,
    *,
    requested_top_k: int,
    config: BroadSchoolPlannerConfig | None = None,
) -> BroadSchoolPlan | None:
    if base_analysis.school_scope not in BROAD_SCHOOL_SCOPE_KINDS or not is_broad_school_scope(
        base_analysis.school_scope
    ):
        return None

    planner_config = config or BroadSchoolPlannerConfig()
    candidate_profiles = _target_profiles_for_scope(base_analysis.school_scope)
    school_limit = _school_limit_for_request(requested_top_k, planner_config)
    selected_profiles = candidate_profiles[:school_limit]
    school_group = group_for_school_scope(base_analysis.school_scope)

    school_queries: list[PlannedSchoolQuery] = []
    for profile in selected_profiles:
        school_query = _build_school_specific_query(base_analysis, profile)
        school_analysis = analyze_query(
            school_query,
            school=profile.canonical_name,
            course=base_analysis.course,
            source_types=base_analysis.source_types,
        )
        school_analysis.planner_hints.update(
            {
                "broad_scope": True,
                "github_query_limit": 4,
                "github_per_query": max(4, planner_config.per_school_candidate_budget * 2),
                "github_candidate_target": max(
                    planner_config.per_school_candidate_budget * 2,
                    planner_config.per_school_candidate_budget + 2,
                ),
            }
        )
        school_queries.append(
            PlannedSchoolQuery(
                profile=profile,
                query=school_query,
                analysis=school_analysis,
                candidate_budget=planner_config.per_school_candidate_budget,
            )
        )

    return BroadSchoolPlan(
        scope_kind=base_analysis.school_scope,
        school_group=school_group,
        scope_note=_scope_note(base_analysis.school_scope, school_group),
        profiles_considered=selected_profiles,
        school_queries=school_queries,
        per_school_candidate_budget=planner_config.per_school_candidate_budget,
        max_total_candidates=planner_config.max_total_candidates,
        max_results_per_school_in_top=planner_config.max_results_per_school_in_top,
    )
