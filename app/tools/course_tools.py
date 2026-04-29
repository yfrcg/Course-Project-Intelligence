from __future__ import annotations

from app.context.context_builder import ContextBuilder
from app.core.service import CourseProjectIntelligenceService
from app.schemas import (
    BuildCourseContextInput,
    CompareCourseProjectsInput,
    CompareCourseProjectsOutput,
    CompareProjectRoutesInput,
    CompareProjectRoutesOutput,
    CourseContextPackOutput,
    GetProjectBriefInput,
    GetProjectBriefOutput,
    InspectCourseProjectInput,
    InspectCourseProjectOutput,
    ListCourseResourcesInput,
    ListCourseResourcesOutput,
    SearchCourseResourcesInput,
    SearchCourseProjectsInput,
    SearchCourseProjectsOutput,
)
from app.utils.text import unique_preserve_order


service = CourseProjectIntelligenceService()


async def search_course_projects_tool(
    query: str,
    school: str | None = None,
    course: str | None = None,
    source_types: list[str] | None = None,
    top_k: int = 5,
    freshness: str | None = None,
    allow_domains: list[str] | None = None,
    deny_domains: list[str] | None = None,
) -> SearchCourseProjectsOutput:
    payload = SearchCourseProjectsInput(
        query=query,
        school=school,
        course=course,
        source_types=source_types or [],
        top_k=top_k,
        freshness=freshness,
        allow_domains=allow_domains or [],
        deny_domains=deny_domains or [],
    )
    return await service.search_course_projects(payload)


def _prefer_broad_resource_search(query: str) -> bool:
    normalized = (query or "").lower()
    broad_terms = [
        "course materials",
        "course resources",
        "study materials",
        "学习资料",
        "课程资料",
        "公开学习资源",
        "notes",
        "lab materials",
    ]
    specific_terms = ["github", "repo", "repository", "仓库", "源码", "compare", "比较"]
    return any(term in normalized for term in broad_terms) and not any(term in normalized for term in specific_terms)


def _build_course_resources_query(
    query: str,
    *,
    include_notes: bool,
    include_labs: bool,
    include_projects: bool,
    include_reports: bool,
) -> str:
    hints: list[str] = []
    if include_notes:
        hints.extend(["course notes", "study materials"])
    if include_labs:
        hints.extend(["labs", "experiment repository"])
    if include_projects:
        hints.extend(["course project", "final assignment"])
    if include_reports:
        hints.extend(["reports", "writeup"])
    return " ".join(unique_preserve_order([query.strip(), *hints])).strip()


async def search_course_resources_tool(
    query: str,
    school: str | None = None,
    course: str | None = None,
    providers: list[str] | None = None,
    top_k: int = 5,
    include_notes: bool = True,
    include_labs: bool = True,
    include_projects: bool = True,
    include_reports: bool = True,
    freshness: str | None = None,
    allow_domains: list[str] | None = None,
    deny_domains: list[str] | None = None,
) -> SearchCourseProjectsOutput:
    payload = SearchCourseResourcesInput(
        query=query,
        school=school,
        course=course,
        providers=providers or [],
        top_k=top_k,
        include_notes=include_notes,
        include_labs=include_labs,
        include_projects=include_projects,
        include_reports=include_reports,
        freshness=freshness,
        allow_domains=allow_domains or [],
        deny_domains=deny_domains or [],
    )
    forwarded_query = _build_course_resources_query(
        payload.query,
        include_notes=payload.include_notes,
        include_labs=payload.include_labs,
        include_projects=payload.include_projects,
        include_reports=payload.include_reports,
    )
    forwarded_payload = SearchCourseProjectsInput(
        query=forwarded_query,
        school=payload.school,
        course=payload.course,
        source_types=payload.providers,
        top_k=payload.top_k,
        freshness=payload.freshness,
        allow_domains=payload.allow_domains,
        deny_domains=payload.deny_domains,
    )
    return await service.search_course_projects(forwarded_payload)


async def build_course_context_tool(
    query: str,
    max_sources: int = 5,
    max_context_chars: int = 6000,
    intended_use: str | None = None,
    source_urls: list[str] | None = None,
    search_results: list[dict] | None = None,
    inspect_results: list[dict] | None = None,
    compare_result: dict | None = None,
) -> CourseContextPackOutput:
    payload = BuildCourseContextInput(
        query=query,
        max_sources=max_sources,
        max_context_chars=max_context_chars,
        intended_use=intended_use,
        source_urls=source_urls,
        search_results=search_results,
        inspect_results=inspect_results,
        compare_result=compare_result,
    )
    builder = ContextBuilder(
        max_sources=payload.max_sources,
        max_context_chars=payload.max_context_chars,
    )
    query_search_output = None
    if not payload.inspect_results and payload.compare_result is None and not payload.search_results and not payload.source_urls:
        search_top_k = max(3, payload.max_sources)
        if _prefer_broad_resource_search(payload.query):
            query_search_output = await search_course_resources_tool(
                query=payload.query,
                top_k=search_top_k,
            )
        else:
            query_search_output = await search_course_projects_tool(
                query=payload.query,
                top_k=search_top_k,
            )
    return builder.build(
        query=payload.query,
        intended_use=payload.intended_use,
        source_urls=payload.source_urls,
        search_results=payload.search_results,
        inspect_results=payload.inspect_results,
        compare_result=payload.compare_result,
        query_search_output=query_search_output,
    )


async def get_project_brief_tool(url: str) -> GetProjectBriefOutput:
    return await service.get_project_brief(GetProjectBriefInput(url=url))


async def compare_project_routes_tool(
    query: str,
    urls: list[str] | None = None,
    top_k: int = 5,
) -> CompareProjectRoutesOutput:
    payload = CompareProjectRoutesInput(
        query=query,
        urls=urls or [],
        top_k=top_k,
    )
    return await service.compare_project_routes(payload)


async def list_course_resources_tool(
    course: str,
    school: str | None = None,
    top_k: int = 5,
) -> ListCourseResourcesOutput:
    payload = ListCourseResourcesInput(
        school=school,
        course=course,
        top_k=top_k,
    )
    return await service.list_course_resources(payload)


async def inspect_course_project_tool(
    repo: str,
    query: str | None = None,
    include_readme: bool = True,
    include_tree: bool = True,
) -> InspectCourseProjectOutput:
    payload = InspectCourseProjectInput(
        repo=repo,
        query=query,
        include_readme=include_readme,
        include_tree=include_tree,
    )
    return await service.inspect_course_project(payload)


async def compare_course_projects_tool(
    repos: list[str],
    query: str | None = None,
    criteria: list[str] | None = None,
    include_details: bool = True,
) -> CompareCourseProjectsOutput:
    payload = CompareCourseProjectsInput(
        repos=repos,
        query=query,
        criteria=criteria or [],
        include_details=include_details,
    )
    return await service.compare_course_projects(payload)
