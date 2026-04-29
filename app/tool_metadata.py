from __future__ import annotations

SEARCH_COURSE_PROJECTS_DESCRIPTION = (
    "Search public university computer science course resources, including course projects, "
    "final assignments, labs, experiment repositories, notes, reports, GitHub or Gitee "
    "repositories, and course-related study materials. Use this tool when the user asks about "
    "university CS courses, course resources, course materials, course projects, labs, notes, "
    "assignments, reports, GitHub references, repositories, or public learning resources."
)

SEARCH_COURSE_RESOURCES_DESCRIPTION = (
    "Search public university computer science course resources and study materials through a "
    "broader entry point, including notes, labs, assignments, reports, repositories, and course "
    "project references. Prefer this tool for broad questions about course information, course "
    "materials, course notes, lab materials, public repositories, or learning resources for a "
    "university CS course."
)

INSPECT_COURSE_PROJECT_DESCRIPTION = (
    "Inspect a GitHub repository that has already been found, then explain what course assets it "
    "contains and what it is suitable to reference. Use this tool when the user asks to analyze a "
    "specific repository, asks whether it has reports, SQL, schema, lab, src, or notes, or asks "
    "what the repository is a good learning reference for. Optional query context is used to judge "
    "fit_for_query."
)

COMPARE_COURSE_PROJECTS_DESCRIPTION = (
    "Compare multiple candidate GitHub course repositories and recommend which one is the best "
    "learning reference for the user's goal. Use this tool when the user asks to compare several "
    "repositories, choose the best one for database design, report structure, code structure, lab "
    "workflow, notes, or implementation reference. Returns recommendation and safety_note."
)

BUILD_COURSE_CONTEXT_DESCRIPTION = (
    "Build an agent-readable context pack from course project or course resource search results, "
    "known source URLs, inspect results, or compare results. "
    "Use this when an AI agent or MCP host needs structured evidence cards, recommended usage, "
    "citation hints, risk flags, and safety notes before answering questions about university CS "
    "course projects, course resources, labs, assignments, reports, repositories, or course materials."
)

SEARCH_COURSE_PROJECTS_TRIGGER_TERMS = [
    "course resources",
    "course materials",
    "labs",
    "notes",
    "assignments",
    "reports",
    "repositories",
    "university cs courses",
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
        "course resources",
        "course materials",
        "labs",
        "notes",
        "assignments",
        "reports",
        "repositories",
        "university cs courses",
    ],
    "search_course_resources": [
        "course resources",
        "course materials",
        "notes",
        "labs",
        "reports",
        "learning resources",
    ],
    "inspect_course_project": [
        "fit_for_query",
        "reports",
        "sql",
        "schema",
        "lab",
        "src",
        "notes",
    ],
    "compare_course_projects": [
        "compare",
        "recommendation",
        "safety_note",
        "code structure",
        "report structure",
    ],
    "build_course_context": [
        "agent-readable",
        "context pack",
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
        "university_cs_courses",
        "course_resources",
        "course_materials",
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
        "broad_course_information",
        "course_resources",
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
        "known_source_urls",
        "inspect_results",
        "compare_results",
    ],
    "follow_up_tools": ["inspect_course_project", "compare_course_projects"],
    "safety_boundary": "learning_reference_only",
}
