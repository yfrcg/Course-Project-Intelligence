from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.config import get_settings
from app.schemas import (
    CompareCourseProjectsOutput,
    CompareProjectRoutesOutput,
    GetProjectBriefOutput,
    InspectCourseProjectOutput,
    ListCourseResourcesOutput,
    SearchCourseProjectsOutput,
)
from app.tools.course_tools import (
    compare_course_projects_tool,
    compare_project_routes_tool,
    get_project_brief_tool,
    inspect_course_project_tool,
    list_course_resources_tool,
    search_course_projects_tool,
)


def create_mcp_server(*, streamable_http_path: str = "/mcp") -> FastMCP:
    settings = get_settings()
    mcp = FastMCP(
        name="Course Project Intelligence MCP Server",
        instructions=(
            "A vertical intelligence and retrieval MCP server for public course-project "
            "research. It is designed for learning references, technical route comparison, "
            "public resource discovery, and risk-aware project intelligence, not for "
            "directly producing submit-ready assignments."
        ),
        log_level=settings.log_level.upper(),
        streamable_http_path=streamable_http_path,
    )

    @mcp.tool(
        name="search_course_projects",
        description=(
            "Search public course-project related repositories, reports, notes, public "
            "resource collections, and web materials, then return structured intelligence results."
        ),
        structured_output=True,
    )
    async def search_course_projects(
        query: str,
        school: str | None = None,
        course: str | None = None,
        source_types: list[str] | None = None,
        top_k: int = 5,
        freshness: str | None = None,
        allow_domains: list[str] | None = None,
        deny_domains: list[str] | None = None,
    ) -> SearchCourseProjectsOutput:
        return await search_course_projects_tool(
            query=query,
            school=school,
            course=course,
            source_types=source_types,
            top_k=top_k,
            freshness=freshness,
            allow_domains=allow_domains,
            deny_domains=deny_domains,
        )

    @mcp.tool(
        name="get_project_brief",
        description=(
            "Extract a structured brief for a public project or web page, including summary, "
            "inferred course, inferred school, tech stack, project type, and risk note."
        ),
        structured_output=True,
    )
    async def get_project_brief(url: str) -> GetProjectBriefOutput:
        return await get_project_brief_tool(url=url)

    @mcp.tool(
        name="compare_project_routes",
        description=(
            "Compare multiple public projects or discovered project candidates and summarize "
            "common modules, differing routes, typical stack choices, and a recommended learning path."
        ),
        structured_output=True,
    )
    async def compare_project_routes(
        query: str,
        urls: list[str] | None = None,
        top_k: int = 5,
    ) -> CompareProjectRoutesOutput:
        return await compare_project_routes_tool(query=query, urls=urls, top_k=top_k)

    @mcp.tool(
        name="compare_course_projects",
        description=(
            "Compare multiple GitHub course-project repositories for task fit, reference value, "
            "and risk-aware recommendation."
        ),
        structured_output=True,
    )
    async def compare_course_projects(
        repos: list[str],
        query: str | None = None,
        criteria: list[str] | None = None,
        include_details: bool = True,
    ) -> CompareCourseProjectsOutput:
        return await compare_course_projects_tool(
            repos=repos,
            query=query,
            criteria=criteria,
            include_details=include_details,
        )

    @mcp.tool(
        name="list_course_resources",
        description=(
            "List public resources for a course, including repositories, blogs, lab materials, "
            "and public experience pages."
        ),
        structured_output=True,
    )
    async def list_course_resources(
        course: str,
        school: str | None = None,
        top_k: int = 5,
    ) -> ListCourseResourcesOutput:
        return await list_course_resources_tool(course=course, school=school, top_k=top_k)

    @mcp.tool(
        name="inspect_course_project",
        description=(
            "Inspect a GitHub repository returned by search_course_projects and return repo type, "
            "score/value level, README summary, root tree, detected assets, reference utility, "
            "and risk-aware next-step suggestions."
        ),
        structured_output=True,
    )
    async def inspect_course_project(
        repo: str,
        query: str | None = None,
        include_readme: bool = True,
        include_tree: bool = True,
    ) -> InspectCourseProjectOutput:
        return await inspect_course_project_tool(
            repo=repo,
            query=query,
            include_readme=include_readme,
            include_tree=include_tree,
        )

    return mcp
