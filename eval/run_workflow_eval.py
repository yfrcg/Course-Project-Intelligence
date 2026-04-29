from __future__ import annotations

import json
import sys
from pathlib import Path

import anyio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas import SearchCourseProjectsInput, SearchCourseProjectsOutput, SearchResultItem
from app.tools import course_tools


def load_cases() -> list[dict]:
    cases_path = ROOT / "eval" / "workflow_queries.jsonl"
    cases: list[dict] = []
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def validate_docs() -> list[str]:
    required_docs = [
        ROOT / "docs" / "agent-workflow.md",
        ROOT / "docs" / "agent-context-pack.md",
        ROOT / "docs" / "tool-routing-guide.md",
        ROOT / "README.md",
    ]
    errors: list[str] = []
    for doc_path in required_docs:
        if not doc_path.exists():
            errors.append(f"missing doc: {doc_path.relative_to(ROOT)}")
    return errors


def workflow_fixtures() -> dict[str, object]:
    return {
        "os_search_results": [
            SearchResultItem(
                title="OS Lab Repo",
                url="https://github.com/example/os-lab",
                source="github",
                source_type="github",
                repo="example/os-lab",
                snippet="Includes report, src, and notes.",
                explanation="Matches operating system lab workflow and report structure.",
                confidence=0.81,
                score=0.88,
                reference_utility=["lab workflow reference", "report structure reference"],
            ).model_dump(mode="json"),
            SearchResultItem(
                title="OS Notes",
                url="https://example.edu/os-notes",
                source="web",
                source_type="web",
                snippet="Public notes and lab summaries.",
                explanation="Useful for notes review.",
                confidence=0.61,
                score=0.57,
            ).model_dump(mode="json"),
        ],
        "single_inspect_result": [
            {
                "repo": "example/java-web-course",
                "url": "https://github.com/example/java-web-course",
                "fit_for_query": "high",
                "task_fit_reason": "Contains report, src, and schema assets for Java Web course design reference.",
                "suggested_usage": ["report structure reference", "src layout reference"],
                "detected_assets": {"has_report": True, "has_src": True, "has_schema": True},
                "reference_utility": ["report structure reference", "schema reference"],
                "why_recommended": "Relevant for Java Web course design reference.",
            }
        ],
        "multi_inspect_results": [
            {
                "repo": "example/db-project-1",
                "url": "https://github.com/example/db-project-1",
                "fit_for_query": "high",
                "task_fit_reason": "Contains schema, report, and src assets.",
                "suggested_usage": ["schema reference"],
                "detected_assets": {"has_report": True, "has_src": True, "has_schema": True},
                "reference_utility": ["schema reference"],
                "why_recommended": "Strong schema and report structure.",
            },
            {
                "repo": "example/db-project-2",
                "url": "https://github.com/example/db-project-2",
                "fit_for_query": "medium",
                "task_fit_reason": "Contains src and notes but weaker schema coverage.",
                "suggested_usage": ["module reference"],
                "detected_assets": {"has_src": True, "has_notes": True},
                "reference_utility": ["module reference"],
                "why_recommended": "Useful for src layout.",
            },
        ],
        "database_compare_result": {
            "query": "这几个仓库哪个更适合数据库课程设计参考",
            "best_overall": "example/db-project-1",
            "summary": "The first repository is structurally stronger.",
            "recommendation": "`example/db-project-1` is more suitable as a learning reference for database schema and report structure.",
            "comparison": [
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
            "safety_note": "Results are for learning reference only and should not be copied directly.",
        },
    }


async def fake_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
    query = payload.query.lower()
    if "compiler" in query:
        results = [
            SearchResultItem(
                title="Compiler Lab Repo",
                url="https://github.com/example/compiler-lab",
                source="github",
                source_type="github",
                repo="example/compiler-lab",
                snippet="Contains lab, report, and src assets.",
                explanation="Matches compiler lab needs.",
                confidence=0.83,
                score=0.87,
                reference_utility=["lab workflow reference"],
            ),
            SearchResultItem(
                title="Compiler Notes",
                url="https://example.edu/compiler-notes",
                source="web",
                source_type="web",
                snippet="Public notes and lab summaries.",
                explanation="Useful for notes review.",
                confidence=0.6,
                score=0.58,
            ),
        ]
    else:
        results = [
            SearchResultItem(
                title="Database Course Project Repo",
                url="https://github.com/example/database-course-project",
                source="github",
                source_type="github",
                repo="example/database-course-project",
                snippet="Includes report, SQL schema, src, and README notes.",
                explanation="Matches database course project scope and includes schema assets.",
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
        ]
    return SearchCourseProjectsOutput(total_found=len(results), results=results)


def validate_context_pack(case: dict, result) -> list[str]:
    errors: list[str] = []
    if result.query != case["query"]:
        errors.append(f"query mismatch for case `{case['case']}`")
    if not result.summary_for_agent:
        errors.append(f"missing summary_for_agent for case `{case['case']}`")
    if not result.evidence_cards:
        errors.append(f"missing evidence_cards for case `{case['case']}`")
        return errors
    first_card = result.evidence_cards[0]
    if not first_card.title:
        errors.append(f"missing evidence card title for case `{case['case']}`")
    if not first_card.source_type:
        errors.append(f"missing evidence card source_type for case `{case['case']}`")
    if not first_card.risk_flags:
        errors.append(f"missing evidence card risk_flags for case `{case['case']}`")
    if not first_card.recommended_usage:
        errors.append(f"missing evidence card recommended_usage for case `{case['case']}`")
    if not result.safety_note:
        errors.append(f"missing safety_note for case `{case['case']}`")
    if not result.agent_usage_guidance:
        errors.append(f"missing agent_usage_guidance for case `{case['case']}`")
    expected_next_tool = case.get("expected_next_tool", "__skip__")
    if expected_next_tool != "__skip__" and result.suggested_next_tool != expected_next_tool:
        errors.append(
            f"unexpected suggested_next_tool `{result.suggested_next_tool}` for case `{case['case']}`, expected `{expected_next_tool}`"
        )
    combined = " ".join(
        [
            result.summary_for_agent,
            result.agent_usage_guidance,
            result.safety_note,
            first_card.citation_hint or "",
        ]
    ).lower()
    if "official course" in combined and "not official" not in combined:
        errors.append(f"public source was framed too strongly for case `{case['case']}`")
    if "copy directly" in combined and "must not" not in combined and "avoid advice" not in combined:
        errors.append(f"no-copy safety framing is unstable for case `{case['case']}`")
    return errors


async def main_async() -> None:
    cases = load_cases()
    fixtures = workflow_fixtures()
    errors = validate_docs()
    original_search = course_tools.service.search_course_projects
    course_tools.service.search_course_projects = fake_search
    try:
        for case in cases:
            result = await course_tools.build_course_context_tool(
                query=case["query"],
                max_sources=5,
                max_context_chars=6000,
                intended_use=case.get("intended_use"),
                source_urls=case.get("source_urls"),
                search_results=fixtures.get(case["search_results_key"]) if case.get("search_results_key") else None,
                inspect_results=fixtures.get(case["inspect_results_key"]) if case.get("inspect_results_key") else None,
                compare_result=fixtures.get(case["compare_result_key"]) if case.get("compare_result_key") else None,
            )
            errors.extend(validate_context_pack(case, result))
    finally:
        course_tools.service.search_course_projects = original_search

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)

    print(f"{len(cases)}/{len(cases)} passed")


if __name__ == "__main__":
    anyio.run(main_async)
