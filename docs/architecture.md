# Architecture

This document describes the current GitHub-focused architecture of Course Project Intelligence MCP Server.

## Layers

```text
app/main.py
  -> app/server.py
    -> app/tools/
      -> app/core/
        -> app/providers/
        -> app/ranking/
        -> app/context/
        -> app/utils/
```

## Responsibilities

- `server`
  - registers MCP tools
  - exposes tool descriptions, schema, and transport configuration
- `tools`
  - converts MCP arguments into schema models
  - forwards requests to the service layer
- `core`
  - query analysis
  - orchestration
  - normalization
  - comparison and resource-list flows
- `providers`
  - provider abstraction is preserved for future extension
  - the active release provider is GitHub
  - non-GitHub providers are retained only as future-extension code paths and are disabled by default
- `ranking`
  - explainable scoring and ordering
- `context`
  - Evidence Pack assembly
  - EvidenceCard normalization
  - risk flag generation
- `utils`
  - shared helpers such as HTTP, text, logging, and GitHub URL normalization

## Main Request Flow

For `search_course_projects`:

1. `app/server.py` registers the MCP tool.
2. `app/tools/course_tools.py` builds `SearchCourseProjectsInput`.
3. `app/core/service.py` runs query analysis and selects enabled providers.
4. the GitHub provider retrieves repository candidates.
5. ranking and normalization convert provider output into stable MCP output.
6. the service returns structured results with warnings and safety framing.

## Design Principles

- keep MCP tool names stable
- keep the provider registry and Evidence Pack abstractions stable
- keep the current release GitHub-only in its formal support claims
- avoid heavy dependencies and generic web crawling
- preserve clear safety boundaries around learning-reference use
