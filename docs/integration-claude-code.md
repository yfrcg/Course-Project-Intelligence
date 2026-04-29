# Claude Code Integration

This document uses example configuration only. Claude Code setup commands and prompts can change with product updates, so adjust to the current version when needed.

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

Stdio with Python:

```bash
claude mcp add course-project-intelligence -- python -m app.main --transport stdio
```

Stdio with the installed console script:

```bash
claude mcp add course-project-intelligence -- course-intel-mcp --transport stdio
```

HTTP:

```bash
claude mcp add --transport http course-project-intelligence http://127.0.0.1:8000/mcp
```

If your local environment supports per-server environment variables, `GITHUB_TOKEN` can be provided optionally for higher GitHub API limits.

## Verify

- Confirm Claude Code can see `search_course_projects`, `search_course_resources`, `inspect_course_project`, and `compare_course_projects`.
- Run `python scripts/smoke_stdio.py`.
- Run a real prompt flow in Claude Code.

## Recommended Prompts

- `Use the course-project-intelligence MCP server to search for NKU OS lab repositories.`
- `Inspect the top repository and explain what parts are useful for learning.`
- `Compare the top three repositories for code structure and report reference value.`

## FAQ

### MCP loaded but the agent does not call a tool

- Explicitly say `Use the course-project-intelligence MCP server`.
- Use request wording closer to the tool descriptions: `course materials`, `labs`, `notes`, `repositories`, `GitHub references`.
- For broad course-material questions, prefer wording that fits `search_course_resources`.

### Tool shows up but calls fail

- Confirm the command is `python -m app.main --transport stdio` or the equivalent console script.
- Re-run `python scripts/smoke_stdio.py`.
- Check whether the current shell can import the package from the repository root.

### GitHub API rate limit

- Provide `GITHUB_TOKEN` when possible.

### Broad scope does not guarantee all 985 or 211 schools

- Broad scope uses profile-based fanout and diversification, not a complete school directory.

### Results are not official course facts

- The output is public course-resource retrieval and repository analysis, not official curriculum data.

## Safety

Use results for course-project research and learning reference only. Do not use the server for direct ghostwriting, direct copying, or plagiarism submission.
