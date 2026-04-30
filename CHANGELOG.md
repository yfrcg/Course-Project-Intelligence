# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### v1.5 github-only-scope-freeze / release-polish

#### Changed

- Scoped official support to GitHub public repositories
- Preserved the 5 MCP tools and kept their names compatible
- Repositioned `search_course_projects` and `search_course_resources` to GitHub-only discovery
- Repositioned `inspect_course_project` to GitHub repository inspection only
- Repositioned `compare_course_projects` to GitHub repository comparison only
- Repositioned `build_course_context` to GitHub Evidence Pack assembly only

#### Added

- Lightweight GitHub URL validation
- Clear non-GitHub rejection path for `inspect_course_project`
- `unsupported_source` handling for non-GitHub `source_urls`
- Conservative `unsupported_source` and `low_confidence` evidence-card behavior for unsupported URLs

#### Docs

- Updated README to GitHub-only positioning
- Updated routing, workflow, context-pack, diagnostics, examples, and eval docs to GitHub-only language
- Removed or downgraded generic web resource claims from the main release path

#### Eval / Smoke / Tests

- Updated eval fixtures to GitHub-only repository scenarios
- Added non-GitHub unsupported cases to workflow validation
- Updated smoke and pytest coverage for GitHub-only descriptions and unsupported URL handling

#### Compatibility

- Preserved provider registry, `EvidenceCard`, `ContextBuilder`, `risk_flags`, `citation_hint`, `source_urls`, and source-type abstractions for future extension
- Kept `search_course_resources` as a wrapper over `search_course_projects`
- Kept `build_course_context` as an Evidence Pack layer rather than a new search engine
