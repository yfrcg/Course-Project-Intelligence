# Agent Workflow

This document describes the final recommended workflow for Course Project Intelligence MCP Server.

The server is for public course-project research and learning reference only. It does not provide official course conclusions, and it must not be used to directly copy code, reports, assignments, or lab results for submission.

## Toolchain Overview

Recommended full chain:

```text
search_course_projects / search_course_resources
        ↓
inspect_course_project
        ↓
compare_course_projects
        ↓
build_course_context
        ↓
Agent answer
```

The tools have distinct roles:

- `search_course_projects`: discover public repositories and project-style learning references
- `search_course_resources`: discover broader course materials; it remains a wrapper over `search_course_projects`
- `inspect_course_project`: analyze one known repository or URL
- `compare_course_projects`: compare multiple candidates
- `build_course_context`: unify search, inspect, compare, or known-source inputs into an agent-readable evidence pack

## Typical Workflows

### Broad Course Resource Search

```text
user asks broad course resource question
        ↓
search_course_resources
        ↓
build_course_context
        ↓
Agent answer
```

Use this when the user asks for course materials, notes, labs, reports, assignments, or public study resources without focusing on one repository yet.

### Single Repository Analysis

```text
user provides GitHub URL
        ↓
inspect_course_project
        ↓
build_course_context
        ↓
Agent answer
```

Use this when the user already knows a repository and wants to understand what parts are referenceable and what risks remain.

### Multiple Repository Comparison

```text
search_course_projects
        ↓
compare_course_projects
        ↓
build_course_context
        ↓
Agent answer
```

Use this when the user asks which candidate is better for database design, report structure, code organization, lab workflow, or similar comparison criteria.

### Final Recommendation Flow

```text
search_course_resources
        ↓
inspect_course_project
        ↓
compare_course_projects
        ↓
build_course_context
        ↓
Agent final recommendation
```

This is the most complete chain when the host needs both discovery and a final grounded answer.

## `build_course_context` Closure Rules

`build_course_context` now supports all of these inputs:

- query-only search path
- known `source_urls`
- existing `search_results`
- existing `inspect_results`
- existing `compare_result`

That means an agent can keep moving forward without forcing every workflow to restart from search.

## Agent Usage Rules

Agents should:

- preserve `citation_hint`
- preserve `risk_flags`
- keep `safety_note`
- frame results as public learning references
- mention when a source is not official
- use repositories for report structure, technical route, module split, schema ideas, experiment workflow, or notes review

Agents should not:

- call GitHub or Gitee repositories official course materials
- encourage direct copying of code, reports, or assignments
- hide source links
- generate directly submittable coursework artifacts
- present repository recommendations as official course answers

## Final Answer Pattern

When the agent answers a user after `build_course_context`, it should rely on:

- `summary_for_agent`
- `evidence_cards`
- `suggested_next_tool`
- `agent_usage_guidance`
- `safety_note`

This keeps the answer grounded, source-visible, and conservative.
