# Tool Routing Guide

This guide explains when an MCP host should prefer each tool in this repository.

The server is for course-project research and learning reference only. It does not support direct ghostwriting, direct code copying, direct report copying, or plagiarism submission.

## Prefer `search_course_resources`

Use `search_course_resources` when the user mainly wants broad course materials discovery:

- course materials
- notes
- lab materials
- reports
- assignments
- public learning resources

`search_course_resources` remains an alias-style wrapper over `search_course_projects`. It improves host routing but does not introduce a separate retrieval stack.

## Prefer `search_course_projects`

Use `search_course_projects` when the user already sounds project- or repository-oriented:

- course projects
- GitHub or Gitee repositories
- experiment code
- repo-style final assignments
- report or writeup repositories

## Prefer `inspect_course_project`

Use `inspect_course_project` when the user gives a concrete repository or URL and asks:

- what parts are referenceable
- whether the repository has `src`, `report`, `sql`, `schema`, `notes`, `lab`, or `readme`
- whether it fits a specific learning goal

## Prefer `compare_course_projects`

Use `compare_course_projects` when the user gives multiple candidates and asks for a recommendation:

- which repository is better for database design
- which one has better report structure
- which one is stronger for lab workflow
- which one is safer to use as learning reference

## Prefer `build_course_context`

Use `build_course_context` when the host needs structured evidence for an AI agent or MCP host:

- the user asks for agent-readable context
- the user asks to organize sources with risk flags and citation hints
- the user asks to summarize how the materials can be referenced
- the host already has `search_results`, `inspect_results`, `compare_result`, or `source_urls`
- the user asks to preserve safety notes while preparing an answer

Example intents:

- `给我的 Agent 整理几个数据库课程设计参考资料，并说明哪些部分能参考。`
- `Help me collect evidence before answering.`
- `Use these known GitHub URLs to build a context pack with risk flags and citation hints.`

## Recommended Routing

- User only wants broad materials: `search_course_resources`
- User wants project/repository discovery: `search_course_projects`
- User gives a concrete URL: `inspect_course_project`
- User gives multiple candidates for comparison: `compare_course_projects`
- User asks for structured context or the host already has prior results: `build_course_context`

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
source_urls
        ↓
build_course_context
        ↓
inspect_course_project
```

## What Hosts Should Not Do

- Do not present public repository code or reports as directly submittable coursework.
- Do not hide the original source.
- Do not turn high-risk repositories into direct submission advice.
- Do not present MCP output as official course conclusions or official syllabus data.
- Do not claim the host will always auto-select the correct tool. These descriptions and hints only improve the probability.
