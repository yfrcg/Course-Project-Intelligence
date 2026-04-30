# Tool Routing Guide

This release is GitHub-only and GitHub-first.

Use the tools like this:

- want to find GitHub course project repositories: `search_course_projects`
- want to find GitHub-hosted labs, assignments, notes, reports, or broader course materials: `search_course_resources`
- already have a GitHub repository URL or `owner/name`: `inspect_course_project`
- already have multiple GitHub repositories and need a recommendation: `compare_course_projects`
- need an agent-readable Evidence Pack: `build_course_context`

## `search_course_projects`

Prefer this tool when the user sounds repository-oriented:

- GitHub repositories
- course projects
- labs
- assignments
- reports
- SQL or schema references
- source code structure

## `search_course_resources`

Prefer this tool when the user asks a broader GitHub resource question:

- course materials on GitHub
- notes
- labs
- reports
- assignments
- repository collections for a course

This tool remains a wrapper over `search_course_projects`.

## `inspect_course_project`

Prefer this tool when the user gives:

- a GitHub repository URL
- a GitHub `owner/name`
- a request to check README, src, report, SQL, schema, notes, lab, assignment, or docs

If the user gives a non-GitHub URL, tell them the current version does not support deep inspection for that source and ask for a GitHub repository URL.

## `compare_course_projects`

Prefer this tool when the user gives multiple GitHub repositories and asks:

- which one is better for database design
- which one has better report structure
- which one is stronger for lab workflow
- which one is safer as a learning reference

## `build_course_context`

Prefer this tool when the host or agent needs:

- Evidence Pack output
- evidence cards
- risk flags
- citation hints
- source-aware safety framing
- reuse of `search_results`, `inspect_results`, `compare_result`, or GitHub `source_urls`

## Recommended Chains

```text
search_course_resources
        ↓
build_course_context
```

```text
search_course_projects
        ↓
inspect_course_project
        ↓
build_course_context
```

```text
search_course_projects
        ↓
compare_course_projects
        ↓
build_course_context
```

```text
GitHub source_urls
        ↓
build_course_context
        ↓
inspect_course_project
```

## Non-GitHub Inputs

For non-GitHub URLs:

- do not claim support
- do not deeply inspect the website
- mark them as `unsupported_source`
- keep `low_confidence`
- ask for a GitHub repository URL instead
