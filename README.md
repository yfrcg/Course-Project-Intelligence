# Course Project Intelligence MCP Server

> A MCP server for course-project research across universities, with explainable search, single-repo inspection, and multi-repo comparison.
>
> 一个面向高校计算机课程项目调研的 MCP Server，支持可解释检索、单仓分析和多仓比较。

`1.0.0rc1` | `v0.8` Broad School Retrieval | `v0.9` Course-Aware Retrieval And Analysis | `v1.0-rc1` Stable Agent Workflow Release

## Language

- [English](#english)
- [中文](#中文)

## English

### Overview

Course Project Intelligence MCP Server helps MCP hosts such as Trae, Cursor, and Claude Code discover and analyze public course-project repositories, lab repos, notes, and collections for learning reference.

It is designed for:

- vertical retrieval of public course-project materials
- query-aware inspection of a single GitHub repository
- comparison of multiple candidate repositories
- explainable output with evidence, risk notes, and safety boundaries

This repository keeps the MCP server source code, docs, host examples, and lightweight validation assets for tool routing and host integration.

### Safety Boundary

- For course-project research and study reference only
- Not for ghostwriting, direct code copying, report copying, or plagiarism submission
- Sources should remain visible
- High-risk repositories should not be framed as directly reusable coursework

Read the full policy in [docs/safety-policy.md](docs/safety-policy.md).

### Core Tools

`search_course_projects`

- Searches public course projects, lab repos, notes, and collections
- Returns fields such as `repo_type`, `score`, `value_level`, `confidence_level`, `why_recommended`, `positive_evidence`, `reference_utility`, `cap_reason`, and `caveat`

`search_course_resources`

- Broad search entry for course materials, notes, labs, reports, repositories, and public learning resources
- Reuses `search_course_projects` retrieval logic as a compatibility wrapper for broader course-material questions

`inspect_course_project`

- Inspects a single GitHub repository
- Supports optional `query` context
- Returns `fit_for_query`, `task_fit_reason`, `suggested_usage`, `not_suitable_for`, `risk_level`, `detected_assets`, `course_profile_id`, and `course_specific_assets`

`compare_course_projects`

- Compares multiple candidate repositories
- Reuses inspect and scorer logic
- Returns `best_overall`, `comparison`, `recommendation`, `failed_repos`, and `safety_note`

`build_course_context`

- Builds an agent-readable context pack from search results
- Also accepts known `source_urls`, prior `search_results`, `inspect_results`, or `compare_result`
- Returns short evidence cards, `risk_flags`, `recommended_usage`, `citation_hint`, `suggested_next_tool`, and `safety_note`

Additional tools:

- `get_project_brief`
- `compare_project_routes`
- `list_course_resources`

### Highlights

- Broad school retrieval for `985` / `211` / `C9` / `双一流` / general university scope
- Course-aware retrieval and analysis with the first 10 course profiles
- Explainable ranking with evidence, risk penalty, and score cap
- README and root-tree enrichment
- Stable `search -> inspect -> compare -> context` workflow for MCP hosts and AI agents

### Quick Start

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

Run with stdio:

```bash
python -m app.main --transport stdio
```

Or use the installed console script:

```bash
course-intel-mcp --transport stdio
```

Run with Streamable HTTP:

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

Default endpoint:

```text
http://127.0.0.1:8000/mcp
```

### Host Integration

Trae:

- [examples/trae/README.md](examples/trae/README.md)
- [examples/trae/python-stdio.mcp.json](examples/trae/python-stdio.mcp.json)
- [examples/trae/stdio.mcp.json](examples/trae/stdio.mcp.json)
- [examples/trae/http.mcp.json](examples/trae/http.mcp.json)
- [examples/trae/demo.md](examples/trae/demo.md)

Cursor:

- [examples/cursor/README.md](examples/cursor/README.md)
- [examples/cursor/python-stdio.mcp.json](examples/cursor/python-stdio.mcp.json)
- [examples/cursor/stdio.mcp.json](examples/cursor/stdio.mcp.json)
- [examples/cursor/http.mcp.json](examples/cursor/http.mcp.json)

Claude Code:

- [examples/claude-code/README.md](examples/claude-code/README.md)
- [examples/claude-code/stdio-python.txt](examples/claude-code/stdio-python.txt)
- [examples/claude-code/stdio-cli.txt](examples/claude-code/stdio-cli.txt)
- [examples/claude-code/http.txt](examples/claude-code/http.txt)

Generic MCP hosts:

- [docs/deployment.md](docs/deployment.md)
- [examples/generic-mcp-host/README.md](examples/generic-mcp-host/README.md)

More host-specific integration guides:

- [docs/integration-trae.md](docs/integration-trae.md)
- [docs/integration-claude-code.md](docs/integration-claude-code.md)
- [docs/integration-cursor.md](docs/integration-cursor.md)

### Host Integration and Tool Routing

This project is a standard MCP server. Trae, Claude Code, Cursor, and other MCP hosts can integrate with it at the protocol layer, but their config entry points, permission prompts, and tool-selection behavior can differ.

For host-adoption work, this repository now provides a prompt cookbook, host-specific test prompts, and a routing diagnostics guide in addition to the base integration docs.

If an MCP host does not proactively call a tool:

- explicitly mention `course-project-intelligence` in the prompt when the host supports named MCP servers
- use wording closer to the tool capability, such as `projects`, `labs`, `notes`, `GitHub`, `repositories`, `course materials`, or `public resources`
- use `search_course_resources` for broad course-material questions when the user did not explicitly ask for a project

Recommended reading:

- [docs/tool-routing-guide.md](docs/tool-routing-guide.md)
- [docs/routing-diagnostics.md](docs/routing-diagnostics.md)
- [docs/agent-context-pack.md](docs/agent-context-pack.md)
- [docs/integration-trae.md](docs/integration-trae.md)
- [docs/integration-claude-code.md](docs/integration-claude-code.md)
- [docs/integration-cursor.md](docs/integration-cursor.md)
- [examples/prompt-cookbook.md](examples/prompt-cookbook.md)
- [examples/host-test-prompts.md](examples/host-test-prompts.md)

Recommended test prompts:

- `Use course-project-intelligence to search course resources about compiler labs.`
- `请使用 course-project-intelligence，帮我找南开大学数据库课程设计相关的公开仓库和课程笔记。`
- `Compare the top three repositories for code structure and report reference value.`

If the host still does not proactively call a tool, use explicit phrasing such as:

- `Use course-project-intelligence to search course resources about ...`

### Agent Context Pack

If the AI host or agent needs structured context rather than plain discovery results, prefer `build_course_context`.

- Use `build_course_context` when the host needs an evidence pack with `risk_flags`, `citation_hint`, and `suggested_next_tool`
- Use `build_course_context` when the host already has `search_results`, `inspect_results`, `compare_result`, or known `source_urls`
- Use `search_course_resources` when the host only needs broad discovery
- Use `inspect_course_project` when the user already gives a specific repository or GitHub URL
- Use `compare_course_projects` when the host needs a recommendation across several candidates

`build_course_context` is an Agent Context Pack tool. It is not a replacement for the underlying search tools.

### Agent Workflow Closure

Recommended closure paths:

```text
search_course_resources
        ↓
build_course_context
        ↓
Agent answer
```

```text
search_course_projects
        ↓
inspect_course_project
        ↓
build_course_context
        ↓
Agent answer
```

```text
search_course_projects
        ↓
compare_course_projects
        ↓
build_course_context
        ↓
Agent answer
```

```text
known source_urls
        ↓
build_course_context
        ↓
inspect_course_project if needed
        ↓
Agent answer
```

### Example Requests

`search_course_projects`

```json
{
  "query": "南开大学 数据库系统 大作业 github",
  "top_k": 5
}
```

`inspect_course_project`

```json
{
  "repo": "lazy-forever/CourseSelectSystem",
  "query": "南开大学 数据库系统 大作业",
  "include_readme": true,
  "include_tree": true
}
```

`build_course_context`

```json
{
  "query": "数据库课程设计参考资料",
  "max_sources": 5,
  "max_context_chars": 6000,
  "intended_use": "study guidance and report-structure analysis",
  "source_urls": ["https://github.com/example/db-project-1"]
}
```

`compare_course_projects`

```json
{
  "repos": [
    "lazy-forever/CourseSelectSystem",
    "le-77-rrg/NKU_DATABASE_SYSTEM"
  ],
  "query": "南开大学 数据库系统 大作业",
  "criteria": ["数据库设计", "模块划分", "报告结构"],
  "include_details": true
}
```

More request samples:

- [examples/sample-requests.json](examples/sample-requests.json)

### Workflow

Recommended flow:

```text
Natural language request
-> search_course_projects or search_course_resources
-> inspect_course_project when needed
-> compare_course_projects when needed
-> build_course_context for the final agent-facing evidence pack
-> learning-reference recommendation with risk reminder
```

More details:

- [docs/tool-reference.md](docs/tool-reference.md)
- [docs/agent-workflow.md](docs/agent-workflow.md)

### Version Timeline

- `v0.8`: Broad School Retrieval
- `v0.9`: Course-Aware Retrieval And Analysis
- `v1.0-rc1`: Stable Agent Workflow Release / Release Candidate

### Repository Layout

- `app/`: MCP server, core logic, providers, ranking, schemas, and tools
- `docs/`: tool reference, workflow, deployment, release notes, and safety policy
- `examples/`: Trae, Cursor, Claude Code, and generic host examples

### Minimal Verification

Recommended quick checks:

```bash
python -m pytest -q
$env:PYTHONPATH='.'; python eval/run_eval.py
$env:PYTHONPATH='.'; python eval/run_agent_context_eval.py
$env:PYTHONPATH='.'; python eval/run_workflow_eval.py
python scripts/smoke_stdio.py
python smoke_test.py
python -m app.main --transport stdio
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

If the tests pass and the two startup commands wait for host connections, the server is runnable and the core routing metadata is in place.

### Limitations

- GitHub is the main working provider in the current release
- Gitee provider remains MVP-level
- Web seed provider is lightweight HTML extraction, not a full search engine or browser renderer
- Broad school retrieval is based on the first batch of school profiles and does not guarantee complete coverage
- Course profiles can still be expanded in future versions

## 中文

### 项目简介

这是一个面向高校计算机课程公开学习参考资源的标准 MCP Server，主要服务于 Trae、Cursor、Claude Code 等 MCP Host，也面向需要结构化上下文的 AI Agent。

它适合以下场景：

- 检索高校 CS 课程相关的公开项目、实验、报告、笔记和仓库
- 分析单个 GitHub 仓库或网页公开资源是否适合当前课程任务
- 比较多个候选仓库的学习参考价值
- 把 search / inspect / compare 结果整理成 Agent 可消费的结构化 Context Pack
- 输出结构化证据、风险提示、引用提示和安全边界

### 使用边界

- 仅用于课程项目调研和学习参考
- 不支持直接代写、复制或抄袭提交
- 不应隐藏来源
- 不应把 GitHub / Gitee / 网页公开仓库包装成官方课程资料
- 不应把高风险仓库包装成可直接复用的作业答案

完整说明见 [docs/safety-policy.md](docs/safety-policy.md)。

### 核心工具

`search_course_projects`

- 检索公开课程项目、实验仓库、课程笔记和资料合集
- 返回 `repo_type`、`score`、`value_level`、`confidence_level`、`why_recommended`、`positive_evidence`、`reference_utility`、`cap_reason`、`caveat`

`search_course_resources`

- 更宽泛的课程资料检索入口，覆盖 `course materials`、`labs`、`notes`、`assignments`、`reports`、`repositories`
- 仍然复用 `search_course_projects` 的检索逻辑，是兼容性包装工具，不是独立搜索栈

`inspect_course_project`

- 分析单个 GitHub 仓库
- 支持可选 `query` 上下文
- 返回 `fit_for_query`、`task_fit_reason`、`suggested_usage`、`not_suitable_for`、`risk_level`、`detected_assets`、`course_profile_id`、`course_specific_assets`

`compare_course_projects`

- 比较多个候选仓库
- 复用 inspect 和 scorer 逻辑
- 返回 `best_overall`、`comparison`、`recommendation`、`failed_repos`、`safety_note`

`build_course_context`

- 构建 Agent Context Pack，把资料整理为结构化 Evidence Pack
- 支持 `query`、已知 `source_urls`、已有 `search_results`、`inspect_results`、`compare_result`
- 返回 `summary_for_agent`、`evidence_cards`、`risk_flags`、`citation_hint`、`suggested_next_tool`、`agent_usage_guidance`、`safety_note`

补充工具：

- `get_project_brief`
- `compare_project_routes`
- `list_course_resources`

### 项目亮点

- 支持 `985` / `211` / `C9` / `双一流` / 泛高校范围检索
- 支持课程 profile 与 course-aware 检索分析
- 支持可解释评分、风险惩罚和 `score cap`
- 支持 README 和根目录结构 enrichment
- 支持稳定的 `search -> inspect -> compare -> build_course_context` Agent 工作流闭环

### 快速开始

创建虚拟环境并安装：

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

使用 stdio 启动：

```bash
python -m app.main --transport stdio
```

或使用已安装的 console script：

```bash
course-intel-mcp --transport stdio
```

使用 HTTP 启动：

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

默认地址：

```text
http://127.0.0.1:8000/mcp
```

### 宿主接入

Trae：

- [examples/trae/README.md](examples/trae/README.md)
- [examples/trae/python-stdio.mcp.json](examples/trae/python-stdio.mcp.json)
- [examples/trae/stdio.mcp.json](examples/trae/stdio.mcp.json)
- [examples/trae/http.mcp.json](examples/trae/http.mcp.json)
- [examples/trae/demo.md](examples/trae/demo.md)

Cursor：

- [examples/cursor/README.md](examples/cursor/README.md)
- [examples/cursor/python-stdio.mcp.json](examples/cursor/python-stdio.mcp.json)
- [examples/cursor/stdio.mcp.json](examples/cursor/stdio.mcp.json)
- [examples/cursor/http.mcp.json](examples/cursor/http.mcp.json)

Claude Code：

- [examples/claude-code/README.md](examples/claude-code/README.md)
- [examples/claude-code/stdio-python.txt](examples/claude-code/stdio-python.txt)
- [examples/claude-code/stdio-cli.txt](examples/claude-code/stdio-cli.txt)
- [examples/claude-code/http.txt](examples/claude-code/http.txt)

通用 MCP Host：

- [docs/deployment.md](docs/deployment.md)
- [examples/generic-mcp-host/README.md](examples/generic-mcp-host/README.md)

更多宿主与路由文档：

- [docs/tool-routing-guide.md](docs/tool-routing-guide.md)
- [docs/routing-diagnostics.md](docs/routing-diagnostics.md)
- [docs/agent-context-pack.md](docs/agent-context-pack.md)
- [docs/agent-workflow.md](docs/agent-workflow.md)
- [docs/integration-trae.md](docs/integration-trae.md)
- [docs/integration-claude-code.md](docs/integration-claude-code.md)
- [docs/integration-cursor.md](docs/integration-cursor.md)
- [examples/prompt-cookbook.md](examples/prompt-cookbook.md)
- [examples/host-test-prompts.md](examples/host-test-prompts.md)

### 宿主接入与工具路由

如果 MCP Host 没有主动调工具：

- 可以显式写 `Use course-project-intelligence to ...`
- 宽泛课程资料问题优先贴近 `search_course_resources`
- 已知具体 GitHub URL 优先贴近 `inspect_course_project`
- 已有 search / inspect / compare 结果，需要整理成 Agent 上下文时优先使用 `build_course_context`

推荐测试提示词：

- `Use course-project-intelligence to search course resources about compiler labs.`
- `请使用 course-project-intelligence，帮我找南开大学数据库课程设计相关的公开仓库和课程笔记。`
- `Use course-project-intelligence to build an agent-readable context pack from these known repository URLs.`

### Agent Context Pack

当 AI Host / Agent 需要的不只是“找到资料”，而是“拿到可引用、可控、带风险提示的上下文”时，应优先调用 `build_course_context`。

- 仅需发现候选资料：`search_course_resources` 或 `search_course_projects`
- 已知具体仓库或 URL：`inspect_course_project`
- 需要比较多个候选：`compare_course_projects`
- 需要把 query、URL、search、inspect、compare 整理成统一证据包：`build_course_context`

`build_course_context` 是 Agent Context Pack 封装层，不是新的搜索引擎。

### 示例请求

`search_course_projects`

```json
{
  "query": "南开大学 数据库系统 大作业 github",
  "top_k": 5
}
```

`inspect_course_project`

```json
{
  "repo": "lazy-forever/CourseSelectSystem",
  "query": "南开大学 数据库系统 大作业",
  "include_readme": true,
  "include_tree": true
}
```

`build_course_context`

```json
{
  "query": "数据库课程设计参考资料",
  "max_sources": 5,
  "max_context_chars": 6000,
  "intended_use": "学习建议和报告结构分析",
  "source_urls": ["https://github.com/example/db-project-1"]
}
```

`compare_course_projects`

```json
{
  "repos": [
    "lazy-forever/CourseSelectSystem",
    "le-77-rrg/NKU_DATABASE_SYSTEM"
  ],
  "query": "南开大学 数据库系统 大作业",
  "criteria": ["数据库设计", "模块划分", "报告结构"],
  "include_details": true
}
```

更多请求样例见：

- [examples/sample-requests.json](examples/sample-requests.json)

### Agent 使用链路

推荐链路：

```text
用户自然语言
-> search_course_projects 或 search_course_resources
-> inspect_course_project（需要时）
-> compare_course_projects（需要时）
-> build_course_context
-> 输出学习参考建议和风险提醒
```

典型闭环：

```text
search_course_resources
        ↓
build_course_context
        ↓
Agent answer
```

```text
search_course_projects
        ↓
inspect_course_project
        ↓
build_course_context
        ↓
Agent answer
```

```text
search_course_projects
        ↓
compare_course_projects
        ↓
build_course_context
        ↓
Agent answer
```

```text
用户直接提供 source_urls
        ↓
build_course_context
        ↓
inspect_course_project（如需要）
        ↓
Agent answer
```

详细说明见：

- [docs/tool-reference.md](docs/tool-reference.md)
- [docs/agent-workflow.md](docs/agent-workflow.md)

### 版本演进

- `v0.8`: Broad School Retrieval
- `v0.9`: Course-Aware Retrieval And Analysis
- `v1.0-rc1`: Stable Agent Workflow Release / Release Candidate

### 仓库结构

- `app/`: MCP server、核心逻辑、provider、ranking、schema 与 tools
- `docs/`: 工具说明、工作流、部署、发布和安全策略文档
- `examples/`: Trae、Cursor、Claude Code 与 generic host 的配置样例

### 最小验证

推荐快速验证：

```bash
python -m pytest -q
$env:PYTHONPATH='.'; python eval/run_eval.py
$env:PYTHONPATH='.'; python eval/run_agent_context_eval.py
$env:PYTHONPATH='.'; python eval/run_workflow_eval.py
python scripts/smoke_stdio.py
python smoke_test.py
python -m app.main --transport stdio
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

如果测试通过，且两个启动命令能够正常等待宿主连接，说明 server 本体、路由元数据和 Agent workflow closure 已处于可用状态。

### 已知限制

- GitHub 是当前版本的主要可运行 provider
- Gitee provider 仍是 MVP 状态
- Web seed provider 是轻量 HTML 抽取，不是完整搜索引擎或浏览器渲染器
- broad school retrieval 基于首批学校 profile，不保证覆盖全部高校
- 课程 profile 后续仍可继续扩充
