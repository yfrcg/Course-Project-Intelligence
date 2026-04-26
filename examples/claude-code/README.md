# Claude Code MCP Example

Run from the repository root after installing the package.

Ready-to-copy command files:

- `stdio-python.txt`
- `stdio-cli.txt`
- `http.txt`

## stdio

```bash
claude mcp add course-project-intelligence -- python -m app.main --transport stdio
```

Or use the installed console script:

```bash
claude mcp add course-project-intelligence -- course-intel-mcp --transport stdio
```

## Streamable HTTP

Start the server:

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

Add it to Claude Code:

```bash
claude mcp add --transport http course-project-intelligence http://127.0.0.1:8000/mcp
```

Use returned results as learning references and route intelligence only. Do not submit public project code as coursework.
