# Agent Context Pack

Agent Context Pack is the GitHub-focused evidence layer for this server.

`build_course_context` turns GitHub repository search, inspect, compare, or provided GitHub URLs into an agent-readable Evidence Pack with:

- `summary_for_agent`
- `evidence_cards`
- `suggested_next_tool`
- `agent_usage_guidance`
- `safety_note`

## Supported Inputs

`build_course_context` supports:

- `query`
- `source_urls`
- `search_results`
- `inspect_results`
- `compare_result`

Expected semantics in this release:

- `query`: GitHub search path
- `source_urls`: intended for GitHub repository URLs
- `search_results`: expected to come from GitHub repository search
- `inspect_results`: expected to come from GitHub repository inspection
- `compare_result`: expected to come from GitHub repository comparison

Non-GitHub URLs in `source_urls` are marked as `unsupported_source` and are not deeply inspected.

## EvidenceCard

Each evidence card contains:

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

## `risk_flags`

Current lightweight risk flags include:

- `not_official`
- `may_be_outdated`
- `copy_risk`
- `low_confidence`
- `broad_query`
- `unknown_source`
- `unsupported_source`

Defaults:

- GitHub repository evidence should keep `not_official`
- non-GitHub URL evidence should keep `unsupported_source` and `low_confidence`
- references to reports, assignments, homework, labs, src, code, course design, experiments, or reports should tend to keep `copy_risk`

## `source_urls`

`source_urls` is intended for GitHub repository URLs.

Behavior:

- GitHub URL: preserved as a normal GitHub evidence candidate
- non-GitHub URL: preserved as `unsupported_source`
- non-GitHub URL: no deep inspection
- non-GitHub URL: recommended usage should tell the agent to ask for a GitHub repository URL

## `suggested_next_tool`

`suggested_next_tool` should help the host continue the GitHub workflow:

- `inspect_course_project` when the pack contains GitHub candidates that should be inspected
- `compare_course_projects` when multiple inspected GitHub candidates should be compared
- `None` when the pack is already ready for a final answer or when only unsupported sources were provided

## Safety

- Evidence Pack sources are public GitHub learning references.
- They are not official course materials.
- Keep `citation_hint`, `risk_flags`, and `safety_note` visible downstream.
- Do not encourage direct copying of code, reports, labs, or assignments.
