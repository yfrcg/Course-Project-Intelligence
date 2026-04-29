from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.server import create_mcp_server
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


def main() -> None:
    server = create_mcp_server()
    tools = {tool.name: tool for tool in server._tool_manager.list_tools()}

    missing = [name for name in CORE_ROUTE_TOOL_NAMES if name not in tools]
    if missing:
        raise RuntimeError(
            "missing tools from FastMCP registration: "
            f"{missing}. Discovered tools: {sorted(tools)}"
        )
    if AGENT_CONTEXT_TOOL_NAME not in tools:
        raise RuntimeError(
            f"missing `{AGENT_CONTEXT_TOOL_NAME}` from FastMCP registration. Discovered tools: {sorted(tools)}"
        )

    print("Core tools registered in FastMCP:")
    for tool_name in CORE_ROUTE_TOOL_NAMES:
        print(f"- {tool_name}")
    print("Agent context tool registered in FastMCP:")
    print(f"- {AGENT_CONTEXT_TOOL_NAME}")

    print("\nDescription keyword checks:")
    for tool_name, terms in CORE_TOOL_DESCRIPTION_CHECKS.items():
        description = (tools[tool_name].description or "").lower()
        matched_terms, missing_terms = _term_statuses(description, terms)
        print(f"- {tool_name}: {_format_ok(not missing_terms)} (checked {len(terms)} terms)")
        print(f"  matched: {matched_terms}")
        print(f"  missing: {missing_terms or ['<none>']}")
        if missing_terms:
            raise RuntimeError(f"{tool_name} description missing expected trigger terms: {missing_terms}")

    resource_meta = tools["search_course_resources"].meta or {}
    print("\nAlias metadata:")
    print(f"- search_course_resources meta: {resource_meta}")
    if resource_meta.get("alias_of") != "search_course_projects":
        raise RuntimeError(
            "search_course_resources alias metadata is invalid. "
            f"Expected alias_of=search_course_projects, got {resource_meta!r}"
        )

    print("\nSchema parameter description checks:")
    for tool_name, field_names in CORE_TOOL_PARAM_DESCRIPTION_FIELDS.items():
        properties = tools[tool_name].parameters.get("properties", {})
        missing_fields = []
        field_statuses = []
        for field_name in field_names:
            field_schema = properties.get(field_name) or {}
            has_description = bool(field_schema.get("description"))
            field_statuses.append(f"{field_name}={_format_ok(has_description)}")
            if not has_description:
                missing_fields.append(field_name)
        print(f"- {tool_name}: {_format_ok(not missing_fields)} (checked {', '.join(field_names)})")
        print(f"  fields: {field_statuses}")
        if missing_fields:
            raise RuntimeError(f"{tool_name} schema is missing parameter descriptions for: {missing_fields}")

    async def fake_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        return SearchCourseProjectsOutput(
            total_found=2,
            results=[
                SearchResultItem(
                    title="Operating System Lab Repo",
                    url="https://github.com/example/os-lab",
                    source="github",
                    source_type="github",
                    repo="example/os-lab",
                    snippet="Includes lab report, src, and README notes.",
                    explanation="Relevant because it exposes operating system lab workflow and report assets.",
                    confidence=0.84,
                    score=0.9,
                    why_recommended="Contains report and src structure for learning reference.",
                    positive_evidence=["report and src assets are visible"],
                    reference_utility=["lab workflow reference", "report structure reference"],
                ),
                SearchResultItem(
                    title="OS Course Notes",
                    url="https://example.edu/os-notes",
                    source="web",
                    source_type="web",
                    snippet="Public notes and lab summaries.",
                    explanation="Useful for overview and notes review.",
                    confidence=0.61,
                    score=0.57,
                    reference_utility=["notes review"],
                ),
            ],
        )

    import anyio

    async def _sample_context_check() -> None:
        original_search = course_tools.service.search_course_projects
        course_tools.service.search_course_projects = fake_search
        try:
            query_only_search_results = await fake_search(SearchCourseProjectsInput(query="operating system course materials"))
            workflow_cases = [
                ("query_only", {"query": "operating system course materials", "max_sources": 2, "intended_use": "study guidance"}),
                (
                    "source_urls",
                    {
                        "query": "analyze these operating system repositories",
                        "source_urls": [
                            "https://github.com/example/os-lab",
                            "https://github.com/example/os-notes",
                        ],
                        "max_sources": 2,
                    },
                ),
                (
                    "search_results",
                    {
                        "query": "operating system course materials",
                        "search_results": [result.model_dump(mode="json") for result in query_only_search_results.results],
                        "max_sources": 2,
                    },
                ),
                (
                    "inspect_results",
                    {
                        "query": "this repo fits OS lab learning",
                        "inspect_results": [
                            {
                                "repo": "example/os-lab",
                                "url": "https://github.com/example/os-lab",
                                "fit_for_query": "high",
                                "task_fit_reason": "Contains lab report, src, and README notes for OS lab workflow.",
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
                        "query": "which OS repository is better",
                        "compare_result": {
                            "best_overall": "example/os-lab",
                            "recommendation": "`example/os-lab` is more suitable as a learning reference.",
                            "comparison": [
                                {
                                    "repo": "example/os-lab",
                                    "url": "https://github.com/example/os-lab",
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

            print("\nSample build_course_context output checks:")
            for case_name, kwargs in workflow_cases:
                context_pack = await course_tools.build_course_context_tool(**kwargs)
                print(f"- {case_name}: {_format_ok(bool(context_pack.summary_for_agent and context_pack.evidence_cards and context_pack.safety_note and context_pack.agent_usage_guidance))}")
                print(f"  suggested_next_tool={context_pack.suggested_next_tool!r}")
                if not context_pack.summary_for_agent or not context_pack.evidence_cards or not context_pack.safety_note or not context_pack.agent_usage_guidance:
                    raise RuntimeError(f"build_course_context `{case_name}` path is missing one or more required structured fields.")
        finally:
            course_tools.service.search_course_projects = original_search

    anyio.run(_sample_context_check)

    print("\npassed")


if __name__ == "__main__":
    main()
