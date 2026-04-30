# Tool Reference

This document summarizes the GitHub-only release contract for the 5 core MCP tools.

## `search_course_projects`

Purpose:

- search public GitHub repositories related to university CS course projects, labs, assignments, reports, notes, SQL, schema, and source code

Key input fields:

- `query`
- `school`
- `course`
- `source_types`
- `top_k`

Key output fields:

- `results`
- `provider_status`
- `warnings`
- `safety_note`

Notes:

- current stable provider is GitHub
- results are learning references only

## `search_course_resources`

Purpose:

- broad GitHub wrapper around `search_course_projects`

Key input fields:

- `query`
- `providers`
- `include_notes`
- `include_labs`
- `include_projects`
- `include_reports`

Notes:

- this tool reuses `search_course_projects`
- it is not a separate search stack

## `inspect_course_project`

Purpose:

- inspect a GitHub repository URL or GitHub `owner/name`

Key input fields:

- `repo`
- `query`
- `include_readme`
- `include_tree`

Key output fields:

- `fit_for_query`
- `task_fit_reason`
- `detected_assets`
- `suggested_usage`
- `risk_level`
- `safety_note`

Unsupported behavior:

- non-GitHub URLs should not be deeply inspected
- non-GitHub URLs should return clear unsupported guidance

## `compare_course_projects`

Purpose:

- compare multiple GitHub repositories as learning references

Key input fields:

- `repos`
- `query`
- `criteria`
- `include_details`

Key output fields:

- `best_overall`
- `comparison`
- `recommendation`
- `failed_repos`
- `safety_note`

## `build_course_context`

Purpose:

- build an agent-readable Evidence Pack from GitHub search, inspect, compare, or provided GitHub `source_urls`

Key input fields:

- `query`
- `source_urls`
- `search_results`
- `inspect_results`
- `compare_result`

Key output fields:

- `summary_for_agent`
- `evidence_cards`
- `suggested_next_tool`
- `agent_usage_guidance`
- `safety_note`

Evidence-card source behavior:

- `github_repo`: supported
- `unknown`: unable to determine
- `unsupported_source`: non-GitHub URL or unsupported source
