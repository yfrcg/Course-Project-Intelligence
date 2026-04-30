# Course Project Intelligence MCP Server

A GitHub-focused MCP server for discovering, inspecting, comparing, and contextualizing public university CS course project repositories as learning references for AI agents.

## Overview

Course Project Intelligence MCP Server is a standard MCP server for hosts such as Trae, Claude Code, and Cursor.

It is built for:

- discovering public GitHub repositories related to university CS course projects
- inspecting GitHub repositories for README, src, report, SQL, schema, notes, lab, assignment, and docs signals
- comparing multiple GitHub repositories as learning references
- building an agent-readable Evidence Pack with source attribution, risk flags, and safety notes

## Release Scope

Officially supported in this release:

- GitHub public repositories
- public GitHub repositories for university CS course projects
- public GitHub repositories for course design, labs, experiment code, reports, notes, SQL, schema, src, and README materials
- GitHub repository search, inspection, comparison, and context-pack construction

Not officially supported in this release:

- non-GitHub websites
- school course websites
- teacher homepages
- blogs and forums
- Gitee or GitLab
- generic webpage crawling
- PDF, DOCX, or PPT deep parsing
- arbitrary URL deep inspection

Rules:

- `source_urls` should point to GitHub repository URLs
- non-GitHub URLs are marked as `unsupported_source`
- results are learning references only
- results are not official course materials
- do not copy code, reports, labs, assignments, or notes directly

## Core MCP Tools

The five core MCP tools are preserved and compatible.

### `search_course_projects`

Search public GitHub repositories related to university CS course projects, labs, assignments, reports, source code, SQL/schema, notes, and course design references.

### `search_course_resources`

A GitHub-focused wrapper around `search_course_projects` for broader GitHub course resource queries.

- reuses `search_course_projects` retrieval logic
- is not a separate search stack

### `inspect_course_project`

Inspect a GitHub repository URL or `owner/name` repository identifier.

- identifies usable learning-reference parts such as README, src, report, SQL, schema, notes, lab, assignment, and docs
- returns clear unsupported guidance for non-GitHub inputs instead of pretending to parse them

### `compare_course_projects`

Compare multiple public GitHub repositories as learning references.

- keeps `recommendation`
- keeps `safety_note`
- keeps conservative non-official framing

### `build_course_context`

Build an agent-readable Evidence Pack from GitHub search, inspect, compare, or provided GitHub `source_urls`.

- non-GitHub URLs are preserved as `unsupported_source`
- unsupported inputs remain low-confidence and are not deeply inspected

## Evidence Pack

`build_course_context` produces a compact Evidence Pack for downstream agents.

Each evidence card includes:

- `title`
- `url`
- `source_type`
- `relevance_reason`
- `usable_parts`
- `risk_flags`
- `recommended_usage`
- `citation_hint`
- `raw_score`

Current release `source_type` guidance:

- `github_repo`: officially supported
- `unknown`: unable to determine
- `unsupported_source`: non-GitHub URL or unsupported source

Current release `risk_flags` include:

- `not_official`
- `may_be_outdated`
- `copy_risk`
- `low_confidence`
- `broad_query`
- `unknown_source`
- `unsupported_source`

## Recommended Workflow

```text
GitHub search
        -> search_course_projects / search_course_resources
        -> inspect_course_project
        -> compare_course_projects
        -> build_course_context
        -> Agent answer
```

Typical usage:

- broad GitHub repo discovery: `search_course_resources`
- project-oriented GitHub repo search: `search_course_projects`
- known GitHub repo URL: `inspect_course_project`
- multiple GitHub repo candidates: `compare_course_projects`
- final agent grounding and citation-ready packaging: `build_course_context`

## Quick Start

Create and activate a virtual environment:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

Run with stdio:

```bash
python -m app.main --transport stdio
```

Run with Streamable HTTP:

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

Default endpoint:

```text
http://127.0.0.1:8000/mcp
```

## Host Integration

Trae:

- [examples/trae/README.md](examples/trae/README.md)
- [examples/trae/python-stdio.mcp.json](examples/trae/python-stdio.mcp.json)
- [examples/trae/stdio.mcp.json](examples/trae/stdio.mcp.json)
- [examples/trae/http.mcp.json](examples/trae/http.mcp.json)

Cursor:

- [examples/cursor/README.md](examples/cursor/README.md)
- [examples/cursor/python-stdio.mcp.json](examples/cursor/python-stdio.mcp.json)
- [examples/cursor/stdio.mcp.json](examples/cursor/stdio.mcp.json)
- [examples/cursor/http.mcp.json](examples/cursor/http.mcp.json)

Claude Code:

- [examples/claude-code/README.md](examples/claude-code/README.md)
- [examples/claude-code/stdio-python.txt](examples/claude-code/stdio-python.txt)
- [examples/claude-code/stdio-cli.txt](examples/claude-code/stdio-cli.txt)
- [examples/claude-code/http.txt](examples/claude-code/http.txt)

## Docs

- [docs/tool-routing-guide.md](docs/tool-routing-guide.md)
- [docs/agent-context-pack.md](docs/agent-context-pack.md)
- [docs/agent-workflow.md](docs/agent-workflow.md)
- [docs/routing-diagnostics.md](docs/routing-diagnostics.md)
- [docs/tool-reference.md](docs/tool-reference.md)
- [docs/architecture.md](docs/architecture.md)
- [examples/prompt-cookbook.md](examples/prompt-cookbook.md)
- [examples/host-test-prompts.md](examples/host-test-prompts.md)
- [eval/README.md](eval/README.md)

## Validation

```bash
python -m pytest -q
python eval/run_eval.py
python eval/run_agent_context_eval.py
python eval/run_workflow_eval.py
python scripts/smoke_stdio.py
python smoke_test.py
```

PowerShell:

```powershell
$env:PYTHONPATH='.'
python eval/run_eval.py
python eval/run_agent_context_eval.py
python eval/run_workflow_eval.py
```

## Safety

- Treat all results as public GitHub learning references.
- Do not describe GitHub repositories as official course materials.
- Keep the source visible in downstream answers.
- Do not directly copy code, reports, labs, assignments, or notes for submission.
- Use the server for research, comparison, and grounded context building, not for submit-ready coursework generation.
