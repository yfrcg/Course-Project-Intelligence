# Routing Diagnostics

This guide helps diagnose MCP host routing for the GitHub-only release.

## Common Reasons No Tool Is Called

- the server is not running
- the host did not refresh its MCP tool list
- the prompt sounds like plain chat instead of GitHub repository retrieval
- the prompt does not mention repositories, GitHub, labs, reports, notes, or course projects

## Common Reasons Only Search Is Called

- the user asked for discovery but not inspection
- the user did not provide a concrete GitHub repository URL
- the user did not ask about README, src, report, SQL, schema, notes, lab, or docs

## Prompts That Route Better

Good routing language:

- GitHub repositories
- course projects
- labs
- assignments
- reports
- notes
- SQL
- schema
- learning references

Examples:

- `Find public GitHub repositories for university operating system labs`
- `Analyze this GitHub repository as a learning reference for a Java Web course project`
- `Compare these GitHub repos for database course design reference`
- `Build an Evidence Pack from these GitHub repository URLs`

## Non-GitHub URL Behavior

If the host gets a non-GitHub URL:

- current release should not pretend to support it
- `inspect_course_project` should reject it clearly
- `build_course_context` should keep it as `unsupported_source`
- the follow-up should ask for a GitHub repository URL

## Server-Side Checks

Run:

```bash
python smoke_test.py
python scripts/smoke_stdio.py
```

These checks confirm:

- all 5 core tools still exist
- tool descriptions are GitHub-only
- core schema descriptions are present
- non-GitHub unsupported behavior is exposed

## Practical Debug Sequence

1. Run `python smoke_test.py`.
2. Run `python scripts/smoke_stdio.py`.
3. Confirm the host lists the 5 core tools.
4. Try an explicit GitHub-oriented prompt.
5. If needed, give a concrete GitHub repository URL.
