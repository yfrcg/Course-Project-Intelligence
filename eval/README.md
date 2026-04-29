# Eval

This repository keeps lightweight eval coverage focused on tool-routing quality and Agent Context Pack stability rather than live host behavior or retrieval quality.

`$env:PYTHONPATH='.'; python eval/run_eval.py` validates:

- the five MCP tools are registered
- `build_course_context` is registered with routing-friendly metadata
- tool descriptions contain the routing trigger terms needed by MCP hosts
- `search_course_resources` exposes alias metadata pointing to `search_course_projects`
- the tool-routing guide, routing diagnostics, Agent Context Pack doc, Agent Workflow doc, host integration docs, and prompt examples are present
- the routing fixtures cover broad Chinese course-material search, English course-material search, lab reports, assignments, repository inspection, multi-repo comparison, explicit server naming, GitHub URL inspection prompts, and mixed host-adoption scenarios

These eval cases primarily test routing intent and metadata quality. They do not test retrieval quality, ranking quality, or actual host-side model decision making.

`$env:PYTHONPATH='.'; python eval/run_agent_context_eval.py` validates the structure stability of `build_course_context`, including `summary_for_agent`, `evidence_cards`, `risk_flags`, `recommended_usage`, `citation_hint`, `suggested_next_tool`, and `safety_note`.

`$env:PYTHONPATH='.'; python eval/run_workflow_eval.py` validates workflow closure across query-only, known `source_urls`, prior `search_results`, prior `inspect_results`, and prior `compare_result`.
