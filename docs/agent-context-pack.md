# Agent Context Pack

Agent Context Pack is a structured evidence layer for AI agents and MCP hosts.

Instead of returning only raw search results, it packages a small set of public learning references into short, controllable evidence cards with usage guidance, risk flags, citation hints, a suggested next tool, and a stable safety note.

## Why It Exists

Normal search output is useful for discovery, but agents still need to decide:

- which sources are most relevant
- which parts are safe to reference
- whether a repository looks unofficial
- whether there is direct copy risk
- whether the agent should inspect one repository or compare several
- how to keep source attribution visible in the final answer

`build_course_context` solves that packaging problem without replacing the existing search tools.

## Supported Inputs

`build_course_context` supports:

- `query`
- `source_urls`
- `search_results`
- `inspect_results`
- `compare_result`

Recommended use:

- use `query` when the host has no prior results
- use `source_urls` when the user or agent already knows candidate links
- use `search_results` when discovery already happened and no re-search is needed
- use `inspect_results` when the host already analyzed one or more repositories
- use `compare_result` when the host already knows the comparison outcome and wants a final answer pack

If only `source_urls` are available, the next recommended step is usually `inspect_course_project`.

If `compare_result` is already available, the context pack is usually ready for the final agent answer.

## How It Differs From Normal Search

`search_course_projects` and `search_course_resources` focus on discovery.

`build_course_context` focuses on agent-readable packaging:

- short summary for the agent
- compact evidence cards
- `risk_flags`
- `recommended_usage`
- `citation_hint`
- `suggested_next_tool`
- stronger downstream safety framing

## EvidenceCard Fields

Each evidence card contains:

- `title`: short source title, repository name, or result label
- `url`: source URL when available
- `source_type`: normalized type such as `github_repo`, `webpage`, `course_material`, or `unknown`
- `relevance_reason`: short explanation of why the source matches the query
- `usable_parts`: what the agent may reference, such as `report`, `src`, `sql`, `schema`, `notes`, `lab`, `assignment`, or `readme`
- `risk_flags`: lightweight safety hints
- `recommended_usage`: short guidance about how to use the source as learning reference
- `citation_hint`: short source wording for downstream attribution
- `raw_score`: original relevance score when available

## `risk_flags`

Current lightweight risk flags include:

- `not_official`
- `may_be_outdated`
- `copy_risk`
- `low_confidence`
- `broad_query`
- `unknown_source`

These are heuristic reminders, not hard blockers. They help the agent avoid overclaiming and keep the answer conservative.

## `citation_hint`

`citation_hint` is not a formal academic citation. It is a short source reminder such as:

- `Learning reference only: <title> - <url>`
- `Learning reference only: <title> - source unavailable`

It helps the agent preserve source visibility without inventing author, year, institution, or official status.

## `recommended_usage`

`recommended_usage` tells the agent what is reasonable to reference from a source.

Examples:

- use for report structure reference
- use for lab workflow comparison
- use for SQL schema learning reference
- inspect further before making detailed claims

This guidance exists to keep answers grounded and to reduce the chance of directly reusing coursework artifacts.

## `suggested_next_tool`

`suggested_next_tool` helps the agent decide what to do next:

- `inspect_course_project` when the pack came from broad search or raw `source_urls`
- `compare_course_projects` when several inspected candidates should be compared next
- `None` when the current pack is already ready for a final answer

## Example Chains

- `build_course_context -> inspect_course_project -> compare_course_projects`
- `search_course_resources -> build_course_context`
- `inspect_course_project -> build_course_context`
- `compare_course_projects -> build_course_context`

## Safety Requirements

- Results are public learning references only.
- They do not represent official course materials or official course conclusions.
- Agents should not present GitHub repositories as official course assets.
- Agents should keep source attribution visible.
- Agents should not encourage directly copying code, reports, or assignments for submission.
