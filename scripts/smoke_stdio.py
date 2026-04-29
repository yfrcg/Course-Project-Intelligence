from __future__ import annotations

import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.tool_metadata import (
    AGENT_CONTEXT_TOOL_NAME,
    CORE_ROUTE_TOOL_NAMES,
    CORE_TOOL_DESCRIPTION_CHECKS,
    CORE_TOOL_PARAM_DESCRIPTION_FIELDS,
)
from app.tools import course_tools
from app.schemas import SearchCourseProjectsInput, SearchCourseProjectsOutput, SearchResultItem


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
        print(
            f"- {tool_name}: {_format_ok(not missing_terms)} "
            f"(checked {len(terms)} terms)"
        )
        print(f"  matched: {matched_terms}")
        print(f"  missing: {missing_terms or ['<none>']}")
        if missing_terms:
            raise RuntimeError(
                f"{tool_name} description is missing expected trigger terms: {missing_terms}"
            )

    resource_meta = getattr(tool_map["search_course_resources"], "meta", None) or {}
    print("\nAlias metadata:")
    print(f"- search_course_resources meta: {resource_meta}")
    if resource_meta.get("alias_of") != "search_course_projects":
        raise RuntimeError(
            "search_course_resources alias metadata is invalid. "
            f"Expected alias_of=search_course_projects, got {resource_meta!r}"
        )

    print("\nSchema parameter description checks:")
    for tool_name, field_names in CORE_TOOL_PARAM_DESCRIPTION_FIELDS.items():
        properties = (tool_map[tool_name].inputSchema or {}).get("properties", {})
        missing_fields: list[str] = []
        field_statuses: list[str] = []
        for field_name in field_names:
            field_schema = properties.get(field_name) or {}
            has_description = bool(field_schema.get("description"))
            field_statuses.append(f"{field_name}={_format_ok(has_description)}")
            if not has_description:
                missing_fields.append(field_name)
        print(
            f"- {tool_name}: {_format_ok(not missing_fields)} "
            f"(checked {', '.join(field_names)})"
        )
        print(f"  fields: {field_statuses}")
        if missing_fields:
            raise RuntimeError(
                f"{tool_name} schema is missing parameter descriptions for: {missing_fields}"
            )

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
                    title="Compiler Course Notes",
                    url="https://example.edu/compiler-notes",
                    source="web",
                    source_type="web",
                    snippet="Public notes and lab materials for compiler courses.",
                    explanation="Useful for notes review and lab preparation.",
                    confidence=0.62,
                    score=0.59,
                    reference_utility=["notes review", "lab preparation"],
                ),
            ],
        )

    original_search = course_tools.service.search_course_projects
    course_tools.service.search_course_projects = fake_search
    try:
        print("\nSample build_course_context output checks:")
        workflow_cases = [
            ("query_only", {"query": "compiler course materials", "max_sources": 2, "intended_use": "agent answer grounding"}),
            (
                "source_urls",
                {
                    "query": "analyze these compiler repositories",
                    "source_urls": [
                        "https://github.com/example/compiler-lab",
                        "https://github.com/example/compiler-notes",
                    ],
                    "max_sources": 2,
                },
            ),
            (
                "search_results",
                {
                    "query": "compiler course materials",
                    "search_results": [result.model_dump(mode="json") for result in (await fake_search(SearchCourseProjectsInput(query="compiler course materials"))).results],
                    "max_sources": 2,
                },
            ),
            (
                "inspect_results",
                {
                    "query": "inspect compiler repo reference value",
                    "inspect_results": [
                        {
                            "repo": "example/compiler-lab",
                            "url": "https://github.com/example/compiler-lab",
                            "fit_for_query": "high",
                            "task_fit_reason": "Contains lab, report, src, and README guidance for compiler learning.",
                            "suggested_usage": ["lab workflow reference", "report structure reference"],
                            "detected_assets": {"has_report": True, "has_src": True, "has_lab": True},
                            "reference_utility": ["lab workflow reference"],
                        }
                    ],
                },
            ),
            (
                "compare_result",
                {
                    "query": "which compiler repo is better",
                    "compare_result": {
                        "best_overall": "example/compiler-lab",
                        "recommendation": "`example/compiler-lab` is more suitable as a learning reference.",
                        "comparison": [
                            {
                                "repo": "example/compiler-lab",
                                "url": "https://github.com/example/compiler-lab",
                                "reason": "Better lab workflow and report coverage.",
                                "best_for": ["lab workflow"],
                                "suggested_usage": ["report structure reference"],
                                "detected_assets": {"has_report": True, "has_src": True},
                            }
                        ],
                    },
                },
            ),
        ]
        for case_name, kwargs in workflow_cases:
            result = await course_tools.build_course_context_tool(**kwargs)
            print(f"- {case_name}: {_format_ok(bool(result.summary_for_agent and result.evidence_cards and result.safety_note and result.agent_usage_guidance))}")
            print(f"  suggested_next_tool={result.suggested_next_tool!r}")
            if not result.summary_for_agent or not result.evidence_cards or not result.safety_note or not result.agent_usage_guidance:
                raise RuntimeError(f"build_course_context `{case_name}` path is missing one or more required structured fields.")
    finally:
        course_tools.service.search_course_projects = original_search

    print("\npassed")


if __name__ == "__main__":
    anyio.run(_run)
