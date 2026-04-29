# Cursor Integration

This document uses example configuration only. Cursor MCP settings and UI paths can change between versions, so adjust to the current Cursor build when needed.

## Start The Server

Recommended stdio entry:

```bash
python -m app.main --transport stdio
```

Optional HTTP entry:

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

## Example Config

Stdio example:

```json
{
  "mcpServers": {
    "course-project-intelligence": {
      "command": "python",
      "args": ["-m", "app.main", "--transport", "stdio"],
      "env": {
        "GITHUB_TOKEN": ""
      }
    }
  }
}
```

HTTP example:

```json
{
  "mcpServers": {
    "course-project-intelligence-http": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

`GITHUB_TOKEN` is optional but recommended for higher GitHub API limits.

## Verify

- Confirm Cursor can see `search_course_projects`, `search_course_resources`, `inspect_course_project`, and `compare_course_projects`.
- Run `python scripts/smoke_stdio.py`.
- Run a real prompt flow in Cursor.

## Recommended Prompts

- `Find public GitHub repositories and notes for Nankai Database System course projects using the MCP server.`
- `Inspect the first result.`
- `Compare the first three results.`

## FAQ

### MCP loaded but the agent does not call a tool

- Mention the MCP server name directly in the prompt.
- Use language closer to the tool descriptions: `course resources`, `notes`, `labs`, `assignments`, `reports`, `repositories`.
- For broad course-material requests, use phrasing that better matches `search_course_resources`.

### Tool shows up but calls fail

- Confirm the repository root is the working directory.
- Confirm the configured command is `python -m app.main --transport stdio` or equivalent.
- Re-run `python scripts/smoke_stdio.py`.

### GitHub API rate limit

- Add `GITHUB_TOKEN` if available.

### Broad scope is incomplete

- Coverage for 985, 211, C9, and other broad scopes is intentionally conservative and not exhaustive.

### Results are not official course information

- The server retrieves and analyzes public learning references, not official school records.

## Safety

Use results for course-project research and learning reference only. Do not use the server for direct ghostwriting, direct copying, or plagiarism submission.
