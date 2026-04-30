from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


SAFETY_NOTE_TEXT = (
    "结果仅用于课程项目调研、学习参考、技术路线比较和公开资料发现，"
    "不支持直接代写、抄袭或作为作业提交。"
)


class SearchCourseProjectsInput(BaseModel):
    query: str = Field(
        ...,
        description="Natural-language query for public GitHub repositories related to university CS course projects, labs, notes, assignments, reports, SQL or schema assets, or course design references.",
    )
    school: Optional[str] = Field(default=None, description="Optional school constraint.")
    course: Optional[str] = Field(default=None, description="Optional course constraint.")
    source_types: List[str] = Field(
        default_factory=list,
        description="Optional source filters. The current stable value is github.",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return.")
    freshness: Optional[str] = Field(default=None, description="Optional freshness hint.")
    allow_domains: List[str] = Field(default_factory=list, description="Allow-list of domains.")
    deny_domains: List[str] = Field(default_factory=list, description="Deny-list of domains.")


class SearchCourseResourcesInput(BaseModel):
    query: str = Field(
        ...,
        description="Broad natural-language query for GitHub-hosted university CS course repositories, labs, notes, assignments, reports, or study materials.",
    )
    school: Optional[str] = Field(default=None, description="Optional school constraint.")
    course: Optional[str] = Field(default=None, description="Optional course constraint.")
    providers: List[str] = Field(
        default_factory=list,
        description="Optional provider filters. The current stable value is github.",
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return.")
    include_notes: bool = Field(default=True, description="Whether to bias toward notes and study materials.")
    include_labs: bool = Field(default=True, description="Whether to bias toward labs and experiment repositories.")
    include_projects: bool = Field(default=True, description="Whether to bias toward course projects and final assignments.")
    include_reports: bool = Field(default=True, description="Whether to bias toward reports and writeups.")
    freshness: Optional[str] = Field(default=None, description="Optional freshness hint.")
    allow_domains: List[str] = Field(default_factory=list, description="Allow-list of domains.")
    deny_domains: List[str] = Field(default_factory=list, description="Deny-list of domains.")


class BuildCourseContextInput(BaseModel):
    query: str = Field(
        ...,
        description="User question about GitHub course project repositories or learning references that the agent wants to turn into a structured evidence pack.",
    )
    max_sources: int = Field(default=5, ge=1, le=10, description="Maximum number of evidence cards to keep in the context pack.")
    max_context_chars: int = Field(default=6000, ge=1200, le=20000, description="Maximum approximate character budget for the structured context pack.")
    intended_use: Optional[str] = Field(
        default=None,
        description="Optional note about how the agent plans to use the references, such as study guidance, topic selection, or report-structure analysis.",
    )
    source_urls: Optional[List[str]] = Field(
        default=None,
        description="Optional known GitHub repository URLs that should be turned into evidence cards without requiring a fresh search. Non-GitHub URLs are marked as unsupported_source.",
    )
    search_results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional existing search results from search_course_projects or search_course_resources that should be reused directly.",
    )
    inspect_results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional existing inspect_course_project results that should be converted into evidence cards without re-running inspection.",
    )
    compare_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional existing compare_course_projects result that should be summarized into the final agent context pack.",
    )


class SearchResultItem(BaseModel):
    title: str
    url: str
    source: str
    source_type: str
    repo: Optional[str] = None
    snippet: str = ""
    school: Optional[str] = None
    school_id: Optional[str] = None
    course: Optional[str] = None
    tech_tags: List[str] = Field(default_factory=list)
    year: Optional[int] = None
    confidence: float = 0.0
    score: Optional[float] = None
    use_case: str = ""
    risk_note: str = ""
    explanation: str = ""
    description: Optional[str] = None
    language: Optional[str] = None
    updated_at: Optional[str] = None
    stars: Optional[int] = None
    intent: Optional[str] = None
    repo_type: Optional[str] = None
    value_level: Optional[str] = None
    confidence_level: Optional[str] = None
    why_recommended: Optional[str] = None
    positive_evidence: List[str] = Field(default_factory=list)
    negative_evidence: List[str] = Field(default_factory=list)
    reference_utility: List[str] = Field(default_factory=list)
    cap_reason: Optional[str] = None
    caveat: Optional[str] = None
    matched_school: Optional[str] = None
    school_evidence: List[str] = Field(default_factory=list)
    school_match_strength: Optional[str] = None
    matched_school_aliases: List[str] = Field(default_factory=list)
    matched_course: Optional[str] = None
    matched_intent: Optional[str] = None
    source_provider: Optional[str] = None
    debug: Dict[str, Any] = Field(default_factory=dict, exclude=True)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchCourseProjectsOutput(BaseModel):
    query_analysis: Dict[str, Any] = Field(default_factory=dict)
    total_found: int = 0
    results: List[SearchResultItem] = Field(default_factory=list)
    provider_status: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    school_scope: Optional[str] = None
    school_group: Optional[str] = None
    scope_note: Optional[str] = None
    scope_coverage: Dict[str, Any] = Field(default_factory=dict)
    safety_note: str = SAFETY_NOTE_TEXT


class EvidenceCardOutput(BaseModel):
    title: str
    url: Optional[str] = None
    source_type: str
    relevance_reason: str
    usable_parts: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    recommended_usage: str
    citation_hint: Optional[str] = None
    raw_score: Optional[float] = None


class CourseContextPackOutput(BaseModel):
    query: str
    intent: str
    summary_for_agent: str
    evidence_cards: List[EvidenceCardOutput] = Field(default_factory=list)
    suggested_next_tool: Optional[str] = None
    agent_usage_guidance: str
    safety_note: str


class GetProjectBriefInput(BaseModel):
    url: str = Field(..., description="Public GitHub repository URL.")


class CitationItem(BaseModel):
    title: str
    url: str
    note: str = ""


class GetProjectBriefOutput(BaseModel):
    title: str
    summary: str
    inferred_course: Optional[str] = None
    inferred_school: Optional[str] = None
    tech_stack: List[str] = Field(default_factory=list)
    project_type: str = ""
    key_points: List[str] = Field(default_factory=list)
    risk_note: str = ""
    citations: List[CitationItem] = Field(default_factory=list)


class CompareProjectRoutesInput(BaseModel):
    query: str = Field(..., description="Comparison target query.")
    urls: List[str] = Field(default_factory=list, description="Optional project URLs.")
    top_k: int = Field(default=5, ge=1, le=20)


class ComparedItem(BaseModel):
    title: str
    url: str
    project_type: str = ""
    inferred_stack: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)


class CompareProjectRoutesOutput(BaseModel):
    compared_items: List[ComparedItem] = Field(default_factory=list)
    common_modules: List[str] = Field(default_factory=list)
    differing_routes: List[str] = Field(default_factory=list)
    typical_stack_choices: List[str] = Field(default_factory=list)
    recommended_learning_path: List[str] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)


class ListCourseResourcesInput(BaseModel):
    school: Optional[str] = Field(default=None, description="Optional school constraint.")
    course: str = Field(..., description="Course name.")
    top_k: int = Field(default=5, ge=1, le=20)


class CourseResourceItem(BaseModel):
    title: str
    url: str
    category: str = ""
    note: str = ""
    source_type: str = ""
    tags: List[str] = Field(default_factory=list)


class ListCourseResourcesOutput(BaseModel):
    school: Optional[str] = None
    course: str
    resources: List[CourseResourceItem] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    citations: List[CitationItem] = Field(default_factory=list)


class QueryAnalysis(BaseModel):
    raw_query: str
    school: Optional[str] = None
    school_id: Optional[str] = None
    detected_schools: List[str] = Field(default_factory=list)
    detected_school_ids: List[str] = Field(default_factory=list)
    school_detection: List[Dict[str, Any]] = Field(default_factory=list)
    school_scope: str = "none"
    scope_evidence: List[str] = Field(default_factory=list)
    course: Optional[str] = None
    course_profile_id: Optional[str] = None
    detected_courses: List[str] = Field(default_factory=list)
    detected_course_ids: List[str] = Field(default_factory=list)
    project_keywords: List[str] = Field(default_factory=list)
    tech_keywords: List[str] = Field(default_factory=list)
    resource_keywords: List[str] = Field(default_factory=list)
    year_hint: Optional[int] = None
    source_types: List[str] = Field(default_factory=list)
    source_type_reasons: List[str] = Field(default_factory=list)
    planner_hints: Dict[str, Any] = Field(default_factory=dict, exclude=True)


class ProviderSearchResult(BaseModel):
    title: str
    url: str
    source: str
    source_type: str
    snippet: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InspectCourseProjectInput(BaseModel):
    repo: str = Field(..., description="GitHub repository in owner/name form or GitHub repository URL.")
    query: Optional[str] = Field(
        default=None,
        description="Optional user task context used to judge fit_for_query without re-running search.",
    )
    include_readme: bool = Field(default=True, description="Whether to summarize README.")
    include_tree: bool = Field(default=True, description="Whether to include the root tree for asset detection.")


class InspectCourseProjectOutput(BaseModel):
    repo: str
    url: Optional[str] = None
    source_provider: Optional[str] = None
    repo_type: str = "unknown"
    school: Optional[str] = None
    school_id: Optional[str] = None
    course: Optional[str] = None
    course_profile_id: Optional[str] = None
    intent: Optional[str] = None
    score: Optional[float] = None
    value_level: Optional[str] = None
    confidence_level: Optional[str] = None
    fit_for_query: str = "unknown"
    task_fit_reason: Optional[str] = None
    not_suitable_for: List[str] = Field(default_factory=list)
    suggested_usage: List[str] = Field(default_factory=list)
    risk_level: str = "medium"
    language: Optional[str] = None
    updated_at: Optional[str] = None
    stars: Optional[int] = None
    error: Optional[str] = None
    readme_summary: Optional[str] = None
    root_tree: List[str] = Field(default_factory=list)
    detected_assets: Dict[str, bool] = Field(default_factory=dict)
    course_specific_assets: Dict[str, bool] = Field(default_factory=dict)
    reference_utility: List[str] = Field(default_factory=list)
    risk_note: Optional[str] = None
    suggested_next_steps: List[str] = Field(default_factory=list)
    reference_suggestions: List[str] = Field(default_factory=list)
    safety_note: str = SAFETY_NOTE_TEXT
    why_recommended: Optional[str] = None
    positive_evidence: List[str] = Field(default_factory=list)
    negative_evidence: List[str] = Field(default_factory=list)
    debug: Dict[str, Any] = Field(default_factory=dict)


class CompareCourseProjectsInput(BaseModel):
    repos: List[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="GitHub repositories in owner/name form or GitHub repository URLs to compare as candidate learning references.",
    )
    query: Optional[str] = Field(
        default=None,
        description="Optional user task context used to evaluate fitness for notes, labs, reports, code structure, or other criteria.",
    )
    criteria: List[str] = Field(default_factory=list, description="Optional comparison criteria.")
    include_details: bool = Field(default=True, description="Whether to include per-repo details.")


class FailedRepoItem(BaseModel):
    repo: str
    error: str


class CompareCourseProjectsItem(BaseModel):
    repo: str
    url: Optional[str] = None
    repo_type: str = "unknown"
    school: Optional[str] = None
    course: Optional[str] = None
    course_profile_id: Optional[str] = None
    intent: Optional[str] = None
    score: Optional[float] = None
    value_level: Optional[str] = None
    confidence_level: Optional[str] = None
    fit_for_query: str = "unknown"
    best_for: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    risk_level: str = "medium"
    reason: str = ""
    reference_utility: List[str] = Field(default_factory=list)
    suggested_usage: List[str] = Field(default_factory=list)
    not_suitable_for: List[str] = Field(default_factory=list)
    detected_assets: Dict[str, bool] = Field(default_factory=dict)
    course_specific_assets: Dict[str, bool] = Field(default_factory=dict)


class CompareCourseProjectsOutput(BaseModel):
    query: Optional[str] = None
    criteria: List[str] = Field(default_factory=list)
    best_overall: Optional[str] = None
    summary: str = ""
    comparison: List[CompareCourseProjectsItem] = Field(default_factory=list)
    failed_repos: List[FailedRepoItem] = Field(default_factory=list)
    recommendation: str = ""
    safety_note: str = SAFETY_NOTE_TEXT
