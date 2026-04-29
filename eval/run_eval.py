from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.server import create_mcp_server


def load_cases() -> list[dict]:
    cases_path = ROOT / "eval" / "queries.jsonl"
    cases: list[dict] = []
    for line in cases_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def load_tool_map():
    server = create_mcp_server()
    return {tool.name: tool for tool in server._tool_manager.list_tools()}


def validate_docs() -> list[str]:
    required_docs = [
        ROOT / "docs" / "tool-routing-guide.md",
        ROOT / "docs" / "routing-diagnostics.md",
        ROOT / "docs" / "agent-context-pack.md",
        ROOT / "docs" / "agent-workflow.md",
        ROOT / "docs" / "integration-trae.md",
        ROOT / "docs" / "integration-claude-code.md",
        ROOT / "docs" / "integration-cursor.md",
        ROOT / "examples" / "prompt-cookbook.md",
        ROOT / "examples" / "host-test-prompts.md",
    ]
    errors: list[str] = []
    for doc_path in required_docs:
        if not doc_path.exists():
            errors.append(f"missing doc: {doc_path.relative_to(ROOT)}")
    return errors


def validate_case(case: dict, tool_map: dict[str, object]) -> list[str]:
    errors: list[str] = []
    expected_tool = case.get("expected_preferred_tool")
    acceptable_tools = case.get("acceptable_tools")
    candidate_tools = [expected_tool] if expected_tool else list(acceptable_tools or [])

    if not candidate_tools:
        return [f"case has no expected tool: {case.get('query')}"]

    present_candidates = [tool_name for tool_name in candidate_tools if tool_name in tool_map]
    if not present_candidates:
        return [f"none of the expected tools are registered for query: {case.get('query')}"]

    target_name = expected_tool or present_candidates[0]
    target = tool_map[target_name]
    description = (target.description or "").lower()
    meta = target.meta or {}

    for term in case.get("required_terms", []):
        if term.lower() not in description:
            errors.append(f"{target_name} description missing term `{term}` for query `{case['query']}`")

    for key, value in case.get("required_meta", {}).items():
        if meta.get(key) != value:
            errors.append(f"{target_name} meta `{key}` expected `{value}` for query `{case['query']}`")

    return errors


def main() -> None:
    tool_map = load_tool_map()
    cases = load_cases()
    errors = validate_docs()

    for case in cases:
        if case.get("type") == "tool_routing":
            errors.extend(validate_case(case, tool_map))

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)

    print(f"{len(cases)}/{len(cases)} passed")


if __name__ == "__main__":
    main()
