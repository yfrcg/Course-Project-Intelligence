from __future__ import annotations

import pytest

from app.schemas import (
    CompareCourseProjectsOutput,
    CourseContextPackOutput,
    InspectCourseProjectOutput,
    SearchCourseProjectsInput,
    SearchCourseProjectsOutput,
    SearchResultItem,
)
from app.server import create_mcp_server
from app.tool_metadata import (
    AGENT_CONTEXT_TOOL_NAME,
    CORE_ROUTE_TOOL_NAMES,
    CORE_TOOL_DESCRIPTION_CHECKS,
    CORE_TOOL_PARAM_DESCRIPTION_FIELDS,
    ROUTING_TOOL_NAMES,
)
from app.tools import course_tools


def _tool_map():
    server = create_mcp_server()
    return {tool.name: tool for tool in server._tool_manager.list_tools()}


def test_core_route_tools_are_registered_with_readable_schema() -> None:
    tool_map = _tool_map()

    for tool_name in ROUTING_TOOL_NAMES:
        assert tool_name in tool_map
        assert tool_map[tool_name].parameters.get("type") == "object"
        assert "properties" in tool_map[tool_name].parameters

    resource_properties = tool_map["search_course_resources"].parameters["properties"]
    assert "providers" in resource_properties
    assert "include_notes" in resource_properties
    assert "include_labs" in resource_properties
    assert "include_projects" in resource_properties
    assert "include_reports" in resource_properties

    context_properties = tool_map[AGENT_CONTEXT_TOOL_NAME].parameters["properties"]
    assert "max_sources" in context_properties
    assert "max_context_chars" in context_properties
    assert "intended_use" in context_properties
    assert "source_urls" in context_properties
    assert "search_results" in context_properties
    assert "inspect_results" in context_properties
    assert "compare_result" in context_properties


def test_core_route_tool_descriptions_and_meta_include_routing_hints() -> None:
    tool_map = _tool_map()

    for tool_name, terms in CORE_TOOL_DESCRIPTION_CHECKS.items():
        description = tool_map[tool_name].description.lower()
        for term in terms:
            assert term in description

    resource_meta = tool_map["search_course_resources"].meta or {}
    assert resource_meta.get("alias_of") == "search_course_projects"
    assert resource_meta.get("mode") == "course_resources"

    context_meta = tool_map[AGENT_CONTEXT_TOOL_NAME].meta or {}
    assert context_meta.get("mode") == "agent_context_pack"
    assert context_meta.get("agent_facing") is True
    assert context_meta.get("output_contract") == "evidence_pack"


def test_core_route_tool_parameter_descriptions_exist() -> None:
    tool_map = _tool_map()

    for tool_name, field_names in CORE_TOOL_PARAM_DESCRIPTION_FIELDS.items():
        properties = tool_map[tool_name].parameters.get("properties", {})
        for field_name in field_names:
            field_schema = properties.get(field_name)
            assert field_schema is not None
            assert field_schema.get("description")


@pytest.mark.asyncio
async def test_search_course_resources_reuses_search_course_projects_service(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        captured["payload"] = payload
        return SearchCourseProjectsOutput(total_found=0, results=[])

    monkeypatch.setattr(course_tools.service, "search_course_projects", fake_search)

    await course_tools.search_course_resources_tool(
        query="南开大学 数据结构 课程资料",
        providers=["github", "web"],
        include_notes=True,
        include_labs=True,
        include_projects=False,
        include_reports=True,
    )

    forwarded_payload = captured["payload"]
    assert isinstance(forwarded_payload, SearchCourseProjectsInput)
    assert forwarded_payload.source_types == ["github", "web"]
    assert "course notes" in forwarded_payload.query
    assert "labs" in forwarded_payload.query
    assert "reports" in forwarded_payload.query
    assert "course project" not in forwarded_payload.query


@pytest.mark.asyncio
async def test_build_course_context_returns_agent_context_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        return SearchCourseProjectsOutput(
            total_found=3,
            results=[
                SearchResultItem(
                    title="NKU Database Course Project Repo",
                    url="https://github.com/example/nku-db-project",
                    source="github",
                    source_type="github",
                    repo="example/nku-db-project",
                    snippet="Includes report, SQL schema, src, and README notes.",
                    explanation="Relevant because it matches database course project scope and includes schema assets.",
                    confidence=0.82,
                    score=0.91,
                    why_recommended="Contains report structure and SQL schema for learning reference.",
                    positive_evidence=["report and sql assets are visible"],
                    reference_utility=["report structure reference", "database schema reference"],
                ),
                SearchResultItem(
                    title="Database Notes Collection",
                    url="https://example.edu/db-notes",
                    source="web",
                    source_type="web",
                    snippet="Public course notes and lab materials.",
                    explanation="Useful for notes and lab workflow reference.",
                    confidence=0.66,
                    score=0.63,
                    reference_utility=["notes review", "lab preparation"],
                ),
            ],
        )

    monkeypatch.setattr(course_tools.service, "search_course_projects", fake_search)

    result = await course_tools.build_course_context_tool(
        query="数据库课程资料",
        max_sources=2,
        intended_use="study guidance",
    )

    assert isinstance(result, CourseContextPackOutput)
    assert result.summary_for_agent
    assert result.evidence_cards
    assert result.safety_note
    assert result.agent_usage_guidance
    assert result.suggested_next_tool in {"inspect_course_project", "compare_course_projects", None}
    first_card = result.evidence_cards[0]
    assert first_card.title
    assert first_card.source_type
    assert first_card.risk_flags
    assert first_card.recommended_usage
    assert first_card.citation_hint
    assert "not official" in result.safety_note.lower()


@pytest.mark.asyncio
async def test_build_course_context_source_urls_path_skips_search(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        raise AssertionError("search should not be called for source_urls-only context building")

    monkeypatch.setattr(course_tools.service, "search_course_projects", fail_search)

    result = await course_tools.build_course_context_tool(
        query="分析这些数据库课程设计仓库能参考什么",
        source_urls=[
            "https://github.com/example/db-project-1",
            "https://github.com/example/db-project-2",
        ],
        max_sources=2,
    )

    assert result.evidence_cards
    assert result.suggested_next_tool == "inspect_course_project"
    assert "not_official" in result.evidence_cards[0].risk_flags


@pytest.mark.asyncio
async def test_build_course_context_search_results_path_skips_search(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        raise AssertionError("search should not be called when search_results are provided")

    monkeypatch.setattr(course_tools.service, "search_course_projects", fail_search)

    result = await course_tools.build_course_context_tool(
        query="操作系统实验报告和源码",
        search_results=[
            SearchResultItem(
                title="OS Lab Repo",
                url="https://github.com/example/os-lab",
                source="github",
                source_type="github",
                repo="example/os-lab",
                snippet="Includes report, src, and notes.",
                explanation="Matches operating system lab workflow and report structure.",
                confidence=0.8,
                score=0.89,
                reference_utility=["lab workflow reference"],
            ).model_dump(mode="json"),
            SearchResultItem(
                title="OS Notes",
                url="https://example.edu/os-notes",
                source="web",
                source_type="web",
                snippet="Public notes and lab summaries.",
                explanation="Useful for notes review.",
                confidence=0.6,
                score=0.57,
            ).model_dump(mode="json"),
        ],
    )

    assert result.evidence_cards
    assert result.summary_for_agent
    assert result.suggested_next_tool in {"inspect_course_project", "compare_course_projects", None}


@pytest.mark.asyncio
async def test_build_course_context_inspect_results_path_skips_search(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        raise AssertionError("search should not be called when inspect_results are provided")

    monkeypatch.setattr(course_tools.service, "search_course_projects", fail_search)

    result = await course_tools.build_course_context_tool(
        query="这个仓库适合参考什么",
        inspect_results=[
            InspectCourseProjectOutput(
                repo="example/java-web-course",
                url="https://github.com/example/java-web-course",
                fit_for_query="high",
                task_fit_reason="Contains report, src, and schema assets for Java Web course design reference.",
                suggested_usage=["report structure reference", "src layout reference"],
                detected_assets={"has_report": True, "has_src": True, "has_schema": True},
                reference_utility=["report structure reference", "schema reference"],
                why_recommended="Relevant for Java Web course design reference.",
            ).model_dump(mode="json")
        ],
    )

    assert result.evidence_cards
    assert result.summary_for_agent
    assert result.suggested_next_tool is None


@pytest.mark.asyncio
async def test_build_course_context_compare_result_path_skips_search(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
        raise AssertionError("search should not be called when compare_result is provided")

    monkeypatch.setattr(course_tools.service, "search_course_projects", fail_search)

    compare_output = CompareCourseProjectsOutput(
        query="这几个仓库哪个更适合数据库课程设计参考",
        best_overall="example/db-project-1",
        summary="The first repository is structurally stronger.",
        recommendation="`example/db-project-1` is more suitable as a learning reference for database schema and report structure.",
        comparison=[
            {
                "repo": "example/db-project-1",
                "url": "https://github.com/example/db-project-1",
                "reason": "Stronger schema coverage and clearer report structure.",
                "best_for": ["schema reference", "report structure"],
                "suggested_usage": ["database design reference"],
                "detected_assets": {"has_schema": True, "has_report": True},
            },
            {
                "repo": "example/db-project-2",
                "url": "https://github.com/example/db-project-2",
                "reason": "Useful for src layout but weaker report coverage.",
                "best_for": ["src layout"],
                "suggested_usage": ["module reference"],
                "detected_assets": {"has_src": True},
            },
        ],
    )

    result = await course_tools.build_course_context_tool(
        query="这几个仓库哪个更适合数据库课程设计参考",
        compare_result=compare_output.model_dump(mode="json"),
    )

    assert result.evidence_cards
    assert result.summary_for_agent
    assert result.suggested_next_tool is None
    assert "official" in result.safety_note.lower()
