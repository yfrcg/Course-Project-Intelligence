# Routing Diagnostics

This document helps diagnose why an MCP host did or did not call the tools in this repository.

The repository can improve tool selection probability through descriptions, schema metadata, examples, and docs. It cannot guarantee that every host model will always auto-call the best tool.

## Common Reasons A Host Does Not Call Any Tool

- The server is not running.
- The host never connected to the server.
- The host connected but did not refresh the tool list.
- The user prompt is too broad and sounds like ordinary conversation rather than course-resource retrieval.
- The user did not mention repositories, course materials, notes, labs, reports, assignments, or public learning resources.
- The host model chose to answer directly instead of using an available tool.

## Common Reasons A Host Calls `search_course_projects` But Not `inspect_course_project`

- The user asked only for discovery, not analysis.
- The host produced search results but the follow-up prompt did not explicitly mention a repository or ranked candidate.
- The user did not ask what a specific repository is suitable for.
- The user did not ask about assets such as reports, SQL, schema, lab, src, or notes.
- The host saw `search_course_projects` as sufficient because the prompt never requested deeper inspection.

## Why Broad Course-Material Questions Sometimes Fall Back To Plain Chat

- A prompt like `讲讲数据结构` or `Tell me about operating systems` sounds like general explanation, not resource retrieval.
- Some hosts respond conversationally unless the prompt contains retrieval-oriented words such as `course materials`, `notes`, `labs`, `reports`, `GitHub`, `repositories`, or the MCP server name.
- Broad requests are more likely to route correctly when phrased as public course-resource discovery, which is exactly why `search_course_resources` exists.

## What Influences Tool Choice

### Descriptions

- Rich tool descriptions increase the chance that the host understands the intent.
- Trigger words like `course resources`, `course materials`, `notes`, `labs`, `assignments`, `reports`, and `repositories` help route broad course-material requests.

### Schema

- Parameter descriptions help the host understand expected inputs.
- Clear fields like `repo`, `query`, `repos`, `providers`, and `include_notes` reduce ambiguity.

### Examples

- Prompt cookbooks and host test prompts help users phrase requests in a way that aligns with tool capabilities.
- Examples matter most when the host model is conservative about tool use.

### Explicit Tool Name Or Server Name

- Mentioning `course-project-intelligence` directly can help when the host supports named MCP servers.
- Example: `Use course-project-intelligence to search course resources about compiler labs.`

## How To Check Whether The Host Can Really See The Tools

At minimum, the host should be able to list these five tools:

- `search_course_projects`
- `search_course_resources`
- `inspect_course_project`
- `compare_course_projects`
- `build_course_context`

If the host has a tool panel, MCP inspector, slash command, or debug view, confirm that all five names appear exactly as above. If the host exposes an MCP tool list operation, use it and verify the same five names are present.

You can verify the server side directly with:

```bash
python smoke_test.py
python scripts/smoke_stdio.py
```

If those pass, the server is exposing the five tools and the core metadata is present.

## How To Use `smoke_stdio.py`

`python scripts/smoke_stdio.py` launches the server through stdio, runs a real MCP `list_tools`, and checks:

- whether the five tools are visible
- whether description trigger terms are present
- whether `search_course_resources` exposes alias metadata
- whether key schema parameter descriptions are present

If this script fails, fix the server-side registration issue before blaming host routing.

## How To Distinguish Failure Modes

### 1. Server not started

- The host cannot connect at all.
- `python -m app.main --transport stdio` or `python -m app.main --transport http ...` may fail immediately.
- `python scripts/smoke_stdio.py` may also fail.

### 2. Host not connected

- The server is runnable locally, but the host does not show the tool list.
- `python scripts/smoke_stdio.py` passes while the host UI shows no tools.
- This usually indicates configuration or host-side connection issues.

### 3. Host sees tools but does not call them

- The host UI lists the tools, but ordinary prompts produce plain chat responses.
- This is usually a prompt-shaping or host-routing behavior issue, not a server crash.
- Use more explicit wording or mention `course-project-intelligence` directly.

### 4. Tool call fails

- The host selects the tool, but the invocation errors.
- Check the host logs and re-run `python scripts/smoke_stdio.py`.
- Confirm the working directory, Python environment, and startup command.

### 5. GitHub rate limit

- Search or inspect may degrade or fail even though the server itself is healthy.
- Add `GITHUB_TOKEN` when possible.
- Rate limiting affects result quality and call reliability, not just routing.

### 6. Query too broad or unstable

- Very broad prompts can produce inconsistent or low-confidence retrieval.
- Encourage users to add school, course, repository, notes, labs, reports, or GitHub hints.
- For broad discovery, prefer `search_course_resources`.

## Practical Debugging Sequence

1. Run `python smoke_test.py`.
2. Run `python scripts/smoke_stdio.py`.
3. Confirm the host lists the five tools.
4. Try an explicit prompt such as `Use course-project-intelligence to search course resources about compiler labs.`
5. If search works but analysis does not, follow with an explicit inspect or compare request.

## Safety Reminder

- Results are public learning references, not official course conclusions.
- Do not present repository code or reports as directly submittable coursework.
