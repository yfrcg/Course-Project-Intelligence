from __future__ import annotations

import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas import SearchCourseProjectsInput, SearchCourseProjectsOutput, SearchResultItem
from app.tool_metadata import (
    AGENT_CONTEXT_TOOL_NAME,
    CORE_ROUTE_TOOL_NAMES,
    CORE_TOOL_DESCRIPTION_CHECKS,
    CORE_TOOL_PARAM_DESCRIPTION_FIELDS,
)
from app.tools import course_tools


DISALLOWED_SUPPORT_PHRASES = [
    "generic web",
    "ordinary webpage",
    "school website",
]


def _format_ok(ok: bool) -> str:
    return "OK" if ok else "FAIL"


def _term_statuses(description: str, terms: list[str]) -> tuple[list[str], list[str]]:
    matched = [term for term in terms if term in description]
    missing = [term for term in terms if term not in description]
    return matched, missing


async def _run() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.main", "--transport", "stdio"],
        cwd=str(ROOT),
    )

    async with stdio_client(server) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools

    tool_map = {tool.name: tool for tool in tools}
    missing_core = [name for name in CORE_ROUTE_TOOL_NAMES if name not in tool_map]
    if missing_core:
        raise RuntimeError(
            "stdio list_tools is missing core tools. "
            f"Expected {CORE_ROUTE_TOOL_NAMES}, missing {missing_core}. "
            f"Discovered tools: {sorted(tool_map)}"
        )
    if AGENT_CONTEXT_TOOL_NAME not in tool_map:
        raise RuntimeError(
            f"stdio list_tools is missing `{AGENT_CONTEXT_TOOL_NAME}`. Discovered tools: {sorted(tool_map)}"
        )

    print("Core tools discovered via stdio list_tools:")
    for tool_name in CORE_ROUTE_TOOL_NAMES:
        print(f"- {tool_name}")
    print("Agent context tool discovered via stdio list_tools:")
    print(f"- {AGENT_CONTEXT_TOOL_NAME}")

    print("\nDescription keyword checks:")
    for tool_name, terms in CORE_TOOL_DESCRIPTION_CHECKS.items():
        description = (tool_map[tool_name].description or "").lower()
        matched_terms, missing_terms = _term_statuses(description, terms)
        print(f"- {tool_name}: {_format_ok(not missing_terms)} (checked {len(terms)} terms)")
        print(f"  matched: {matched_terms}")
        print(f"  missing: {missing_terms or ['<none>']}")
        if missing_terms:
            raise RuntimeError(f"{tool_name} description is missing expected trigger terms: {missing_terms}")
        bad_terms = [phrase for phrase in DISALLOWED_SUPPORT_PHRASES if phrase in description]
        if bad_terms:
            raise RuntimeError(f"{tool_name} description still contains unsupported web phrasing: {bad_terms}")

    print("\nSchema parameter description checks:")
    for tool_name, field_names in CORE_TOOL_PARAM_DESCRIPTION_FIELDS.items():
        properties = (tool_map[tool_name].inputSchema or {}).get("properties", {})
        missing_fields: list[str] = []
        for field_name in field_names:
            field_schema = properties.get(field_name) or {}
            if not field_schema.get("description"):
                missing_fields.append(field_name)
        print(f"- {tool_name}: {_format_ok(not missing_fields)}")
        if missing_fields:
            raise RuntimeError(f"{tool_name} schema is missing parameter descriptions for: {missing_fields}")

    async def fake_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        return SearchCourseProjectsOutput(
            total_found=2,
            results=[
                SearchResultItem(
                    title="Compiler Lab Reference Repo",
                    url="https://github.com/example/compiler-lab",
                    source="github",
                    source_type="github",
                    repo="example/compiler-lab",
                    snippet="Contains lab notes, src, report, and README guidance.",
                    explanation="Relevant because it matches compiler lab materials and repository signals.",
                    confidence=0.81,
                    score=0.88,
                    why_recommended="Contains lab code and report structure for learning reference.",
                    positive_evidence=["lab and src assets are visible"],
                    reference_utility=["compiler lab workflow", "report structure reference"],
                ),
                SearchResultItem(
                    title="Compiler Notes Repo",
                    url="https://github.com/example/compiler-notes",
                    source="github",
                    source_type="github",
                    repo="example/compiler-notes",
                    snippet="Contains notes and README guidance.",
                    explanation="Useful for notes review and topic scoping.",
                    confidence=0.73,
                    score=0.78,
                    reference_utility=["notes review"],
                ),
            ],
        )

    original_search = course_tools.service.search_course_projects
    course_tools.service.search_course_projects = fake_search
    try:
        query_only = await course_tools.build_course_context_tool(
            query="compiler github lab repositories",
            max_sources=2,
        )
        github_sources = await course_tools.build_course_context_tool(
            query="analyze these compiler repositories",
            source_urls=[
                "https://github.com/example/compiler-lab",
                "github.com/example/compiler-notes",
            ],
            max_sources=2,
        )
        unsupported_sources = await course_tools.build_course_context_tool(
            query="analyze this school page",
            source_urls=["https://example.edu/compiler"],
            max_sources=1,
        )
        unsupported_inspect = await course_tools.inspect_course_project_tool(
            repo="https://example.edu/compiler",
            query="compiler course page",
        )

        if not query_only.evidence_cards or query_only.evidence_cards[0].source_type != "github_repo":
            raise RuntimeError("query_only build_course_context did not produce GitHub evidence cards.")
        if github_sources.suggested_next_tool != "inspect_course_project":
            raise RuntimeError("GitHub source_urls should recommend inspect_course_project.")
        if unsupported_sources.evidence_cards[0].source_type != "unsupported_source":
            raise RuntimeError("Non-GitHub source_urls should be marked as unsupported_source.")
        if "low_confidence" not in unsupported_sources.evidence_cards[0].risk_flags:
            raise RuntimeError("Non-GitHub source_urls should include low_confidence.")
        if unsupported_sources.suggested_next_tool is not None:
            raise RuntimeError("Non-GitHub source_urls should not recommend inspect_course_project.")
        if not unsupported_inspect.error or "unsupported_source" not in unsupported_inspect.error:
            raise RuntimeError("inspect_course_project should reject non-GitHub URLs with unsupported_source.")
    finally:
        course_tools.service.search_course_projects = original_search

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'version = "1.0.0rc1"' not in pyproject:
        raise RuntimeError("pyproject.toml version changed unexpectedly.")

    print("\npassed")


if __name__ == "__main__":
    anyio.run(_run)
