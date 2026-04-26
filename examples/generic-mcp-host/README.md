# Generic MCP Host Example

## stdio

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

## Streamable HTTP

Start the server:

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

Connect the host to:

```text
http://127.0.0.1:8000/mcp
```

The server currently exposes six tools: `search_course_projects`, `inspect_course_project`, `compare_course_projects`, `get_project_brief`, `compare_project_routes`, and `list_course_resources`.

Use all returned results only for course-project research and study reference. Do not use this MCP server for direct ghostwriting, code copying, or plagiarism submission.
