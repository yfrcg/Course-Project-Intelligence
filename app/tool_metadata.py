from __future__ import annotations

SEARCH_COURSE_PROJECTS_DESCRIPTION = (
    "Search public GitHub repositories related to university computer science course projects, "
    "labs, assignments, reports, source code, SQL or schema assets, notes, and course design "
    "references. Use this tool when the user asks for public GitHub repositories that can serve "
    "as learning references for university CS course projects, labs, assignments, reports, or "
    "course design work. Results are learning references only, not official course materials."
)

SEARCH_COURSE_RESOURCES_DESCRIPTION = (
    "A GitHub-focused wrapper around search_course_projects for broader university computer "
    "science course resource queries such as labs, assignments, notes, reports, repositories, "
    "and course materials hosted in public GitHub repositories. Prefer this tool for broad "
    "GitHub repository discovery when the user asks for course materials or learning references "
    "rather than a specific repository."
)

INSPECT_COURSE_PROJECT_DESCRIPTION = (
    "Inspect a specific GitHub repository URL or owner/name repository identifier and identify "
    "usable learning-reference parts such as README, src, reports, SQL, schema, notes, lab, "
    "assignment, or docs. If the input is not a GitHub repository URL or GitHub owner/name "
    "identifier, return invalid_github_url or unsupported_source instead of attempting non-GitHub "
    "deep inspection. Optional query context is used to judge fit_for_query."
)

COMPARE_COURSE_PROJECTS_DESCRIPTION = (
    "Compare multiple public GitHub repositories as learning references for university computer "
    "science course projects. Use this tool when the user asks to compare several GitHub "
    "repositories, choose the best one for database design, report structure, code structure, lab "
    "workflow, notes, or implementation reference. Returns recommendation and safety_note."
)

BUILD_COURSE_CONTEXT_DESCRIPTION = (
    "Build an agent-readable Evidence Pack from public GitHub repository search, inspect, or "
    "compare results, or from provided GitHub repository source_urls. Non-GitHub URLs are kept as "
    "unsupported_source with conservative risk flags instead of being deeply inspected. Use this "
    "when an AI agent or MCP host needs structured evidence cards, recommended usage, citation "
    "hints, risk flags, and safety notes before answering questions about university CS course "
    "project repositories."
)

SEARCH_COURSE_PROJECTS_TRIGGER_TERMS = [
    "public github repositories",
    "course projects",
    "labs",
    "assignments",
    "reports",
    "learning references",
]

CORE_ROUTE_TOOL_NAMES = [
    "search_course_projects",
    "search_course_resources",
    "inspect_course_project",
    "compare_course_projects",
]

AGENT_CONTEXT_TOOL_NAME = "build_course_context"

ROUTING_TOOL_NAMES = [*CORE_ROUTE_TOOL_NAMES, AGENT_CONTEXT_TOOL_NAME]

CORE_TOOL_DESCRIPTION_CHECKS = {
    "search_course_projects": [
        "public github repositories",
        "learning references",
        "course projects",
        "labs",
        "assignments",
        "reports",
        "sql",
    ],
    "search_course_resources": [
        "github-focused wrapper",
        "public github repositories",
        "course materials",
        "notes",
        "labs",
        "reports",
        "learning references",
    ],
    "inspect_course_project": [
        "github repository",
        "invalid_github_url",
        "unsupported_source",
        "fit_for_query",
        "reports",
        "sql",
        "schema",
        "assignment",
    ],
    "compare_course_projects": [
        "public github repositories",
        "recommendation",
        "safety_note",
        "code structure",
        "report structure",
    ],
    "build_course_context": [
        "evidence pack",
        "public github repository",
        "source_urls",
        "unsupported_source",
        "evidence cards",
        "risk flags",
        "safety notes",
    ],
}

CORE_TOOL_PARAM_DESCRIPTION_FIELDS = {
    "search_course_projects": ["query", "source_types", "allow_domains", "deny_domains"],
    "search_course_resources": [
        "query",
        "providers",
        "include_notes",
        "include_labs",
        "include_projects",
        "include_reports",
    ],
    "inspect_course_project": ["repo", "query", "include_readme", "include_tree"],
    "compare_course_projects": ["repos", "query", "criteria", "include_details"],
    "build_course_context": [
        "query",
        "max_sources",
        "max_context_chars",
        "intended_use",
        "source_urls",
        "search_results",
        "inspect_results",
        "compare_result",
    ],
}

SEARCH_COURSE_PROJECTS_META = {
    "route_stage": "search",
    "tool_family": "course-project-intelligence",
    "preferred_for": [
        "github_public_repositories",
        "course_projects",
        "labs",
        "notes",
        "assignments",
        "reports",
        "repositories",
    ],
    "follow_up_tools": ["inspect_course_project", "compare_course_projects"],
    "safety_boundary": "learning_reference_only",
}

SEARCH_COURSE_RESOURCES_META = {
    "route_stage": "search",
    "tool_family": "course-project-intelligence",
    "alias_of": "search_course_projects",
    "mode": "course_resources",
    "preferred_for": [
        "github_course_resources",
        "course_materials",
        "notes",
        "labs",
        "assignments",
        "reports",
        "repositories",
    ],
    "follow_up_tools": ["inspect_course_project", "compare_course_projects"],
    "safety_boundary": "learning_reference_only",
}

INSPECT_COURSE_PROJECT_META = {
    "route_stage": "inspect",
    "tool_family": "course-project-intelligence",
    "preferred_for": [
        "specific_repository_analysis",
        "github_repository_url",
        "query_fit_check",
        "asset_detection",
        "reports_sql_schema_lab_src_notes",
    ],
    "typical_inputs": ["repo", "query"],
    "follow_up_tools": ["compare_course_projects"],
    "safety_boundary": "learning_reference_only",
}

COMPARE_COURSE_PROJECTS_META = {
    "route_stage": "compare",
    "tool_family": "course-project-intelligence",
    "preferred_for": [
        "candidate_comparison",
        "best_reference_selection",
        "database_design",
        "report_structure",
        "code_structure",
        "lab_workflow",
    ],
    "typical_inputs": ["repos", "query", "criteria"],
    "returns": ["recommendation", "safety_note"],
    "safety_boundary": "learning_reference_only",
}

BUILD_COURSE_CONTEXT_META = {
    "route_stage": "context",
    "tool_family": "course-project-intelligence",
    "mode": "agent_context_pack",
    "agent_facing": True,
    "uses": ["search_course_projects", "search_course_resources", "inspect_course_project", "compare_course_projects"],
    "output_contract": "evidence_pack",
    "preferred_for": [
        "agent_context",
        "evidence_cards",
        "citation_hints",
        "risk_flags",
        "safety_notes",
        "known_github_source_urls",
        "inspect_results",
        "compare_results",
    ],
    "follow_up_tools": ["inspect_course_project", "compare_course_projects"],
    "safety_boundary": "learning_reference_only",
}
