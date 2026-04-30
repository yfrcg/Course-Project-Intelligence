# Agent Workflow

This document defines the final GitHub-only workflow for Course Project Intelligence MCP Server.

## Standard Flow

```text
GitHub search
        ↓
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

## Roles

- `search_course_projects`: discover GitHub course project repositories
- `search_course_resources`: broad GitHub wrapper for labs, assignments, notes, reports, and repository materials
- `inspect_course_project`: inspect one GitHub repository URL or `owner/name`
- `compare_course_projects`: compare multiple GitHub repositories
- `build_course_context`: assemble the final Evidence Pack

## Typical Chains

Broad GitHub discovery:

```text
search_course_resources
        ↓
build_course_context
        ↓
Agent answer
```

Known GitHub repository:

```text
inspect_course_project
        ↓
build_course_context
        ↓
Agent answer
```

Comparison workflow:

```text
search_course_projects
        ↓
inspect_course_project
        ↓
compare_course_projects
        ↓
build_course_context
        ↓
Agent answer
```

## Non-GitHub Inputs

If the user gives a non-GitHub URL:

- do not claim support
- do not deeply inspect the site
- mark it as `unsupported_source`
- keep `low_confidence`
- ask for a GitHub repository URL

## Final Answer Rules

- frame all results as public GitHub learning references
- do not frame them as official course conclusions
- keep source attribution visible
- do not encourage direct copying of code, reports, labs, assignments, or notes
