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
    cases_path = ROOT / "eval" / "agent_context_queries.jsonl"
    cases: list[dict] = []
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def validate_docs() -> list[str]:
    required_docs = [
        ROOT / "docs" / "agent-context-pack.md",
        ROOT / "docs" / "agent-workflow.md",
        ROOT / "docs" / "tool-routing-guide.md",
        ROOT / "README.md",
    ]
    errors: list[str] = []
    for doc_path in required_docs:
        if not doc_path.exists():
            errors.append(f"missing doc: {doc_path.relative_to(ROOT)}")
    return errors


async def fake_search(payload: SearchCourseProjectsInput) -> SearchCourseProjectsOutput:
    query = payload.query.lower()
    if "java web" in query:
        results = [
            _repo_result(
                title="Java Web Course Design Repo",
                url="https://github.com/example/java-web-course-design",
                snippet="Contains report, src, schema, and README notes.",
                explanation="Matches Java Web course design reference needs and exposes code structure.",
                why="Includes report structure and src layout for learning reference.",
                utility=["report structure reference", "src layout reference"],
                score=0.9,
            ),
            _web_result(
                title="Java Web Course Notes",
                url="https://example.edu/java-web-notes",
                snippet="Public notes and design summaries.",
                explanation="Useful for notes review and topic scoping.",
                utility=["notes review"],
                score=0.58,
            ),
        ]
    elif "操作系统" in query or "operating system" in query:
        results = [
            _repo_result(
                title="OS Lab Repo",
                url="https://github.com/example/os-lab",
                snippet="Includes lab report, src, README, and experiment notes.",
                explanation="Matches operating system lab workflow and source-code reference needs.",
                why="Contains lab report and src structure for learning reference.",
                utility=["lab workflow reference", "report structure reference"],
                score=0.88,
            ),
            _web_result(
                title="Operating System Course Notes",
                url="https://example.edu/os-notes",
                snippet="Public notes and experiment summaries.",
                explanation="Useful for notes review.",
                utility=["notes review"],
                score=0.55,
            ),
        ]
    elif "编译原理" in query or "compiler" in query:
        results = [
            _repo_result(
                title="Compiler Lab Reference Repo",
                url="https://github.com/example/compiler-lab",
                snippet="Contains lab notes, parser src, report, and README guidance.",
                explanation="Matches compiler lab materials and repository signals.",
                why="Contains lab code and report structure for learning reference.",
                utility=["compiler lab workflow", "report structure reference"],
                score=0.86,
            ),
            _web_result(
                title="Compiler Course Notes",
                url="https://example.edu/compiler-notes",
                snippet="Public notes and lab materials for compiler courses.",
                explanation="Useful for notes review and lab preparation.",
                utility=["notes review", "lab preparation"],
                score=0.61,
            ),
        ]
    else:
        results = [
            _repo_result(
                title="Database Course Project Repo",
                url="https://github.com/example/database-course-project",
                snippet="Includes report, SQL schema, src, and README notes.",
                explanation="Matches database course project scope and includes schema assets.",
                why="Contains report structure and SQL schema for learning reference.",
                utility=["report structure reference", "database schema reference"],
                score=0.91,
            ),
            _repo_result(
                title="Database Homework Collection",
                url="https://github.com/example/database-homework",
                snippet="Assignments, reports, and code samples.",
                explanation="Useful for identifying common assignment structure and risk factors.",
                why="Shows assignment and report patterns.",
                utility=["assignment scope review"],
                score=0.67,
            ),
            _web_result(
                title="Database Course Notes",
                url="https://example.edu/database-notes",
                snippet="Public notes and lab materials.",
                explanation="Useful for notes review and terminology alignment.",
                utility=["notes review", "lab preparation"],
                score=0.63,
            ),
        ]
    return SearchCourseProjectsOutput(total_found=len(results), results=results)


def _repo_result(
    *,
    title: str,
    url: str,
    snippet: str,
    explanation: str,
    why: str,
    utility: list[str],
    score: float,
) -> SearchResultItem:
    return SearchResultItem(
        title=title,
        url=url,
        source="github",
        source_type="github",
        repo=url.split("github.com/")[-1],
        snippet=snippet,
        explanation=explanation,
        confidence=0.82,
        score=score,
        why_recommended=why,
        positive_evidence=["public repository signals are visible"],
        reference_utility=utility,
    )


def _web_result(
    *,
    title: str,
    url: str,
    snippet: str,
    explanation: str,
    utility: list[str],
    score: float,
) -> SearchResultItem:
    return SearchResultItem(
        title=title,
        url=url,
        source="web",
        source_type="web",
        snippet=snippet,
        explanation=explanation,
        confidence=0.63,
        score=score,
        reference_utility=utility,
    )


def validate_context_pack(case: dict, result) -> list[str]:
    errors: list[str] = []
    if not result.summary_for_agent:
        errors.append(f"missing summary_for_agent for query `{case['query']}`")
    if not result.evidence_cards:
        errors.append(f"missing evidence_cards for query `{case['query']}`")
        return errors
    first_card = result.evidence_cards[0]
    if not first_card.title:
        errors.append(f"first evidence card missing title for query `{case['query']}`")
    if not first_card.source_type:
        errors.append(f"first evidence card missing source_type for query `{case['query']}`")
    if not first_card.risk_flags:
        errors.append(f"first evidence card missing risk_flags for query `{case['query']}`")
    if not first_card.recommended_usage:
        errors.append(f"first evidence card missing recommended_usage for query `{case['query']}`")
    if not first_card.citation_hint or "learning reference only:" not in first_card.citation_hint.lower():
        errors.append(f"first evidence card missing stable citation_hint for query `{case['query']}`")
    if not result.safety_note:
        errors.append(f"missing safety_note for query `{case['query']}`")
    if result.suggested_next_tool not in {"inspect_course_project", "compare_course_projects", None}:
        errors.append(f"unexpected suggested_next_tool `{result.suggested_next_tool}` for query `{case['query']}`")
    combined = " ".join(
        [
            result.summary_for_agent,
            result.agent_usage_guidance,
            result.safety_note,
            first_card.recommended_usage,
        ]
    ).lower()
    if "not official" not in combined:
        errors.append(f"context pack does not clearly preserve non-official framing for query `{case['query']}`")
    if "must not be copied directly" not in combined and "avoid advice that suggests copying" not in combined:
        errors.append(f"context pack does not clearly preserve no-copy guidance for query `{case['query']}`")
    return errors


async def main_async() -> None:
    cases = load_cases()
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
