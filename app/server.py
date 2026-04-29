from __future__ import annotations

from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from app.config import get_settings
from app.schemas import (
    CourseContextPackOutput,
    CompareCourseProjectsOutput,
    CompareProjectRoutesOutput,
    GetProjectBriefOutput,
    InspectCourseProjectOutput,
    ListCourseResourcesOutput,
    SearchCourseProjectsOutput,
)
from app.tool_metadata import (
    BUILD_COURSE_CONTEXT_DESCRIPTION,
    BUILD_COURSE_CONTEXT_META,
    COMPARE_COURSE_PROJECTS_DESCRIPTION,
    COMPARE_COURSE_PROJECTS_META,
    INSPECT_COURSE_PROJECT_DESCRIPTION,
    INSPECT_COURSE_PROJECT_META,
    SEARCH_COURSE_PROJECTS_DESCRIPTION,
    SEARCH_COURSE_PROJECTS_META,
    SEARCH_COURSE_RESOURCES_DESCRIPTION,
    SEARCH_COURSE_RESOURCES_META,
)
from app.tools.course_tools import (
    build_course_context_tool,
    compare_course_projects_tool,
    compare_project_routes_tool,
    get_project_brief_tool,
    inspect_course_project_tool,
    list_course_resources_tool,
    search_course_resources_tool,
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
        description=SEARCH_COURSE_PROJECTS_DESCRIPTION,
        meta=SEARCH_COURSE_PROJECTS_META,
        structured_output=True,
    )
    async def search_course_projects(
        query: Annotated[
            str,
            Field(
                description="University CS course query for course resources, course materials, projects, labs, notes, assignments, reports, or repositories."
            ),
        ],
        school: Annotated[str | None, Field(description="Optional school constraint.")] = None,
        course: Annotated[str | None, Field(description="Optional course constraint.")] = None,
        source_types: Annotated[
            list[str] | None,
            Field(description="Optional source filters such as github, gitee, or web."),
        ] = None,
        top_k: Annotated[int, Field(description="Number of results to return.")] = 5,
        freshness: Annotated[str | None, Field(description="Optional freshness hint.")] = None,
        allow_domains: Annotated[list[str] | None, Field(description="Optional allow-list of domains.")] = None,
        deny_domains: Annotated[list[str] | None, Field(description="Optional deny-list of domains.")] = None,
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
        name="search_course_resources",
        description=SEARCH_COURSE_RESOURCES_DESCRIPTION,
        meta=SEARCH_COURSE_RESOURCES_META,
        structured_output=True,
    )
    async def search_course_resources(
        query: Annotated[
            str,
            Field(
                description="Broad university CS course query for course resources, course materials, notes, labs, assignments, reports, or repositories."
            ),
        ],
        school: Annotated[str | None, Field(description="Optional school constraint.")] = None,
        course: Annotated[str | None, Field(description="Optional course constraint.")] = None,
        providers: Annotated[
            list[str] | None,
            Field(description="Optional provider filters such as github, gitee, or web."),
        ] = None,
        top_k: Annotated[int, Field(description="Number of results to return.")] = 5,
        include_notes: Annotated[bool, Field(description="Bias toward notes and course study materials.")] = True,
        include_labs: Annotated[bool, Field(description="Bias toward labs and experiment repositories.")] = True,
        include_projects: Annotated[
            bool,
            Field(description="Bias toward course projects and final assignments."),
        ] = True,
        include_reports: Annotated[bool, Field(description="Bias toward reports and writeups.")] = True,
        freshness: Annotated[str | None, Field(description="Optional freshness hint.")] = None,
        allow_domains: Annotated[list[str] | None, Field(description="Optional allow-list of domains.")] = None,
        deny_domains: Annotated[list[str] | None, Field(description="Optional deny-list of domains.")] = None,
    ) -> SearchCourseProjectsOutput:
        return await search_course_resources_tool(
            query=query,
            school=school,
            course=course,
            providers=providers,
            top_k=top_k,
            include_notes=include_notes,
            include_labs=include_labs,
            include_projects=include_projects,
            include_reports=include_reports,
            freshness=freshness,
            allow_domains=allow_domains,
            deny_domains=deny_domains,
        )

    @mcp.tool(
        name="build_course_context",
        description=BUILD_COURSE_CONTEXT_DESCRIPTION,
        meta=BUILD_COURSE_CONTEXT_META,
        structured_output=True,
    )
    async def build_course_context(
        query: Annotated[
            str,
            Field(
                description="User question about course resources or project references that should be turned into an agent-readable context pack."
            ),
        ],
        max_sources: Annotated[int, Field(description="Maximum number of evidence cards to keep.")] = 5,
        max_context_chars: Annotated[int, Field(description="Maximum approximate character budget for the context pack.")] = 6000,
        intended_use: Annotated[
            str | None,
            Field(description="Optional note about how the agent plans to use the references, such as study guidance or report analysis."),
        ] = None,
        source_urls: Annotated[
            list[str] | None,
            Field(description="Optional known repository or webpage URLs that should be turned into evidence cards without a fresh search."),
        ] = None,
        search_results: Annotated[
            list[dict] | None,
            Field(description="Optional existing search results from search_course_projects or search_course_resources to reuse directly."),
        ] = None,
        inspect_results: Annotated[
            list[dict] | None,
            Field(description="Optional existing inspect_course_project results to reuse directly."),
        ] = None,
        compare_result: Annotated[
            dict | None,
            Field(description="Optional existing compare_course_projects result to summarize into the final context pack."),
        ] = None,
    ) -> CourseContextPackOutput:
        return await build_course_context_tool(
            query=query,
            max_sources=max_sources,
            max_context_chars=max_context_chars,
            intended_use=intended_use,
            source_urls=source_urls,
            search_results=search_results,
            inspect_results=inspect_results,
            compare_result=compare_result,
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
        description=COMPARE_COURSE_PROJECTS_DESCRIPTION,
        meta=COMPARE_COURSE_PROJECTS_META,
        structured_output=True,
    )
    async def compare_course_projects(
        repos: Annotated[
            list[str],
            Field(description="GitHub repositories in owner/name form to compare as candidate learning references."),
        ],
        query: Annotated[
            str | None,
            Field(description="Optional user task context such as notes, lab workflow, database design, or report structure."),
        ] = None,
        criteria: Annotated[list[str] | None, Field(description="Optional comparison criteria.")] = None,
        include_details: Annotated[bool, Field(description="Whether to include per-repo details.")] = True,
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
        description=INSPECT_COURSE_PROJECT_DESCRIPTION,
        meta=INSPECT_COURSE_PROJECT_META,
        structured_output=True,
    )
    async def inspect_course_project(
        repo: Annotated[str, Field(description="GitHub repository in owner/name form.")],
        query: Annotated[
            str | None,
            Field(description="Optional user task context used to judge fit_for_query and reference value."),
        ] = None,
        include_readme: Annotated[bool, Field(description="Whether to summarize README.")] = True,
        include_tree: Annotated[
            bool,
            Field(description="Whether to include the root tree for SQL, schema, report, lab, src, and note detection."),
        ] = True,
    ) -> InspectCourseProjectOutput:
        return await inspect_course_project_tool(
            repo=repo,
            query=query,
            include_readme=include_readme,
            include_tree=include_tree,
        )

    return mcp
