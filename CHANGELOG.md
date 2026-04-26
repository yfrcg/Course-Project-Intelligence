# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- Release notes for `v1.0-rc1`
- Release checklist for `v1.0-rc1`
- Expanded eval documentation covering search / inspect / compare, school scope, course profiles, course-specific assets, and safety checks

### Changed
- Unified public version wording across README, docs, and examples: `v0.8` = Broad School Retrieval, `v0.9` = Course-Aware Retrieval And Analysis, `v1.0-rc1` = Stable Agent Workflow Release

## [1.0.0rc1] - 2026-04-26

### Added
- Stable `search -> inspect -> compare` Agent workflow release candidate
- Broad school retrieval for `985` / `211` / `C9` / `双一流` / broad university scope queries
- Course-aware profiles for the first 10 computer-science courses
- Expanded eval and smoke coverage for school scope, course profile detection, course-specific assets, and safety constraints
- Documentation hardening across README, tool reference, workflow, eval, release notes, and release checklist

### Changed
- `search_course_projects` now combines school-scope planning, course-aware query planning, README/root-tree enrichment, and explainable ranking as a stable release path
- `inspect_course_project` now stably preserves query context, `course_profile_id`, and `course_specific_assets`
- `compare_course_projects` now stably supports criteria + course profile comparison while keeping safety framing
- Source value evaluation is now documented as a stable release capability together with `repo_type` classification and score-cap risk control
- Release wording is aligned to `v0.8` / `v0.9` / `v1.0-rc1` without changing MCP interfaces

### Safety
- Preserved the learning-only safety boundary: only for course-project research and study reference
- Continued to reject direct ghostwriting, code copying, report copying, and plagiarism submission framing
- Continued to require source attribution and conservative handling of high-risk repositories

### Compatibility
- Preserved existing MCP tool names and primary input contracts
- Preserved compatibility for `search_course_projects`, `inspect_course_project`, and `compare_course_projects`

## [0.9.0] - 2026-04-26

### Added
- Course profiles for the first 10 computer-science courses in the initial course-aware rollout
- Course-aware query analysis fields: `course_profile_id`, `detected_courses`, and `detected_course_ids`
- Course-aware inspect/compare output fields: `course_profile_id` and `course_specific_assets`
- New course-aware tests covering course profiles, course detection, query planning, scoring, inspect, compare, and eval quality

### Changed
- `retrieval_profiles` and broad school planner now generate course-aware GitHub queries using course aliases, intent hints, and structure signals
- scorer now uses course-specific structure signals, course-specific reference utility, and negative signals to shape ranking and score caps
- `inspect_course_project` and `compare_course_projects` now preserve course-aware analysis through the returned structured fields
- `eval/run_eval.py` and `eval/queries.jsonl` now validate course-aware outputs across database, operating system, compiler, algorithms, machine learning, and computer networks scenarios
- `retrieval_intents.py` now treats negated phrases such as `不要408题解` more conservatively and avoids misclassifying them as `solution`
- README, tool reference, agent workflow, and Trae demo documentation now describe course-aware behavior and fields

## [0.8.0] - 2026-04-26

### Added
- Broad school retrieval for `985` / `211` / `C9` / `双一流` / broad university scope queries
- University profile groups for the first 20 schools in the initial rollout
- School scope detection for `specific_school`, `multiple_schools`, `project_985`, `project_211`, `c9`, `double_first_class`, `broad_university`, and `none`
- Broad scope response metadata: `school_scope`, `school_group`, `scope_note`, and `scope_coverage`
- Tests for university profiles, school scope detection, broad school planner, broad search behavior, eval quality, and broad workflow compatibility

### Changed
- `search_course_projects` now plans broad scope retrieval by school profile fanout instead of stuffing all aliases into one GitHub query
- Added per-school candidate budgeting, school coverage diversification, and broad-scope confidence constraints
- `eval/run_eval.py` now supports direct execution from the repository root without requiring `PYTHONPATH=.`
- Broad scope eval fixtures now synthesize inspectable per-school repositories for `search -> inspect -> compare` validation
- README, tool reference, agent workflow, and Trae demo documentation now describe broad scope limits and safety boundaries

### Compatibility
- Preserved existing MCP tool names and primary input contracts
- Preserved compatibility for `search_course_projects`, `inspect_course_project`, and `compare_course_projects`
- Preserved the learning-only safety boundary: no direct ghostwriting, copying, or plagiarism submission support

## [0.3.0] - 2026-04-24

### Added
- Trae IDE MCP configuration examples
- Console script entry point for local MCP startup
- stdio MCP smoke test
- Deployment documentation for Trae integration

### Changed
- Improved deployment instructions for stdio and HTTP transports

### Compatibility
- Preserved all existing MCP tool names and schemas
- Preserved existing provider interfaces

## [0.2.0] - 2026-04-24

### Added
- Project governance files: `LICENSE`, `CHANGELOG.md`, and `CONTRIBUTING.md`
- `docs/` documentation set for architecture, provider development, safety, and deployment
- Provider registry to decouple provider construction and selection from core service orchestration
- Lightweight `eval/` harness for contract checks on structured search output
- GitHub Actions CI workflow for Python 3.10 and 3.11
- README hardening for release status, testing, eval, safety boundaries, and host integration

### Changed
- Internal provider wiring to use a registry-based selection path while preserving MCP tool contracts
- Release documentation and contributor guidance for a publishable open source baseline

## [0.1.0] - 2026-04-23

### Added
- Initial Course Project Intelligence MCP Server MVP
- Four MCP tools for search, brief extraction, route comparison, and resource listing
- GitHub, Gitee, and Web seed providers
- `stdio` and Streamable HTTP transports
- Baseline tests for query analysis, ranking, service orchestration, and server registration
