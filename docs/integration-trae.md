# Trae Integration

This document uses example configuration only. Trae UI paths and confirmation flows may change between versions, so adjust to the current Trae build when needed.

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

Console-script variant:

```json
{
  "mcpServers": {
    "course-project-intelligence": {
      "command": "course-intel-mcp",
      "args": ["--transport", "stdio"],
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

`GITHUB_TOKEN` is optional but recommended when you want a higher GitHub API rate limit.

## Verify

- Confirm Trae can see `search_course_projects`, `search_course_resources`, `inspect_course_project`, and `compare_course_projects`.
- Run `python scripts/smoke_stdio.py`.
- Run a real prompt flow inside Trae.

## Recommended Prompts

- `请使用 course-project-intelligence，帮我找南开大学数据结构课程相关的公开项目、实验仓库和课程笔记。`
- `分析第一个仓库适合参考什么。`
- `比较前三个仓库哪个更适合参考课程笔记和实验代码结构。`

## FAQ

### MCP loaded but the agent does not call a tool

- Explicitly mention `course-project-intelligence` in the prompt.
- Use wording closer to the tool descriptions, such as `项目`, `实验`, `笔记`, `GitHub`, `公开资料`, or `课程资料`.
- For broad course-material questions, prefer prompting toward `search_course_resources`.

### Tool shows up but calls fail

- Re-run `python scripts/smoke_stdio.py`.
- Confirm the working directory is the repository root.
- Confirm the selected command actually starts `python -m app.main --transport stdio`.

### GitHub API rate limit

- Add `GITHUB_TOKEN`.
- Retry later if the current window is exhausted.

### Broad scope does not cover every 985 or 211 school

- Broad scope is heuristic and profile-based. It does not guarantee complete coverage.

### Results are not official course information

- The server searches public learning references and repositories. It is not an official course-catalog or syllabus authority.

## Safety

Use results for course-project research and learning reference only. Do not use the server for direct ghostwriting, direct copying, or plagiarism submission.
