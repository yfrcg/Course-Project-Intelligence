# Eval

This repository keeps lightweight eval coverage focused on GitHub-only tool routing and Evidence Pack stability rather than live host behavior or retrieval quality.

`$env:PYTHONPATH='.'; python eval/run_eval.py` validates:

- the five MCP tools are registered
- core tool descriptions are GitHub-only and routing-friendly
- `search_course_resources` still exposes alias metadata pointing to `search_course_projects`
- the main docs and examples for routing and context-pack usage are present
- routing fixtures cover GitHub repo search, inspect, compare, and Evidence Pack prompts

`$env:PYTHONPATH='.'; python eval/run_agent_context_eval.py` validates the structure stability of `build_course_context`, including `summary_for_agent`, `evidence_cards`, `risk_flags`, `recommended_usage`, `citation_hint`, `suggested_next_tool`, and `safety_note`, using GitHub-repository-style fixtures.

`$env:PYTHONPATH='.'; python eval/run_workflow_eval.py` validates workflow closure across query-only, GitHub `source_urls`, prior `search_results`, prior `inspect_results`, and prior `compare_result`, and includes non-GitHub unsupported cases that must emit `unsupported_source` and `low_confidence`.
