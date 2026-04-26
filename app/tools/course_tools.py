from __future__ import annotations

from app.core.service import CourseProjectIntelligenceService
from app.schemas import (
    CompareCourseProjectsInput,
    CompareCourseProjectsOutput,
    CompareProjectRoutesInput,
    CompareProjectRoutesOutput,
    GetProjectBriefInput,
    GetProjectBriefOutput,
    InspectCourseProjectInput,
    InspectCourseProjectOutput,
    ListCourseResourcesInput,
    ListCourseResourcesOutput,
    SearchCourseProjectsInput,
    SearchCourseProjectsOutput,
)


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
