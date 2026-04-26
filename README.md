# Course Project Intelligence MCP Server

> A MCP server for course-project research across universities, with explainable search, single-repo inspection, and multi-repo comparison.
>
> 一个面向高校计算机课程项目调研的 MCP Server，支持可解释检索、单仓分析和多仓比较。

`1.0.0rc1` | `v0.8` Broad School Retrieval | `v0.9` Course-Aware Retrieval And Analysis | `v1.0-rc1` Stable Agent Workflow Release

## Language

- [English](#english)
- [中文](#中文)

## English

### Overview，

Course Project Intelligence MCP Server helps MCP hosts such as Trae, Cursor, and Claude Code discover and analyze public course-project repositories, lab repos, notes, and collections for learning reference.

It is designed for:

- vertical retrieval of public course-project materials
- query-aware inspection of a single GitHub repository
- comparison of multiple candidate repositories
- explainable output with evidence, risk notes, and safety boundaries

This repository is a slim GitHub release repository: it keeps the plugin source code, docs, and host examples, but does not include the internal `tests/`, `eval/`, or `smoke` assets used during development.

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

`inspect_course_project`

- Inspects a single GitHub repository
- Supports optional `query` context
- Returns `fit_for_query`, `task_fit_reason`, `suggested_usage`, `not_suitable_for`, `risk_level`, `detected_assets`, `course_profile_id`, and `course_specific_assets`

`compare_course_projects`

- Compares multiple candidate repositories
- Reuses inspect and scorer logic
- Returns `best_overall`, `comparison`, `recommendation`, `failed_repos`, and `safety_note`

Additional tools:

- `get_project_brief`
- `compare_project_routes`
- `list_course_resources`

### Highlights

- Broad school retrieval for `985` / `211` / `C9` / `双一流` / general university scope
- Course-aware retrieval and analysis with the first 10 course profiles
- Explainable ranking with evidence, risk penalty, and score cap
- README and root-tree enrichment
- Stable `search -> inspect -> compare` workflow for MCP hosts

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
-> search_course_projects
-> inspect_course_project
-> compare_course_projects
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

Since this release repository does not include the internal validation assets, the minimum manual checks are:

```bash
python -m app.main --transport stdio
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

If both commands start successfully and wait for host connections, the plugin itself is runnable.

### Limitations

- GitHub is the main working provider in the current release
- Gitee provider remains MVP-level
- Web seed provider is lightweight HTML extraction, not a full search engine or browser renderer
- Broad school retrieval is based on the first batch of school profiles and does not guarantee complete coverage
- Course profiles can still be expanded in future versions

## 中文

### 项目简介

这是一个面向高校计算机课程项目调研的 MCP Server，主要服务于 Trae、Cursor、Claude Code 等 MCP Host，用于检索和分析公开课程项目、大作业仓库、实验仓库、课程笔记与资料合集。

它适合以下场景：

- 检索公开课程项目和实验资料
- 分析单个 GitHub 仓库是否适合当前课程任务
- 比较多个候选仓库的参考价值
- 输出结构化证据、风险提示和安全边界

当前 GitHub 仓库是一个精简发布仓库：保留了插件本体、文档和宿主接入示例，不再包含开发阶段使用的内部 `tests/`、`eval/`、`smoke` 校验资产。

### 使用边界

- 仅用于课程项目调研和学习参考
- 不支持直接代写、复制或抄袭提交
- 不应隐藏来源
- 不应把高风险仓库包装成可直接复用的作业答案

完整说明见 [docs/safety-policy.md](docs/safety-policy.md)。

### 核心工具

`search_course_projects`

- 检索公开课程项目、实验仓库、课程笔记和资料合集
- 返回 `repo_type`、`score`、`value_level`、`confidence_level`、`why_recommended`、`positive_evidence`、`reference_utility`、`cap_reason`、`caveat`

`inspect_course_project`

- 分析单个 GitHub 仓库
- 支持可选 `query` 上下文
- 返回 `fit_for_query`、`task_fit_reason`、`suggested_usage`、`not_suitable_for`、`risk_level`、`detected_assets`、`course_profile_id`、`course_specific_assets`

`compare_course_projects`

- 比较多个候选仓库
- 复用 inspect 和 scorer 逻辑
- 返回 `best_overall`、`comparison`、`recommendation`、`failed_repos`、`safety_note`

补充工具：

- `get_project_brief`
- `compare_project_routes`
- `list_course_resources`

### 项目亮点

- 支持 `985` / `211` / `C9` / `双一流` / 泛高校范围检索
- 支持课程 profile 与 course-aware 检索分析
- 支持可解释评分、风险惩罚和 `score cap`
- 支持 README 和根目录结构 enrichment
- 支持稳定的 `search -> inspect -> compare` Agent 工作流

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
-> search_course_projects
-> inspect_course_project
-> compare_course_projects
-> 输出学习参考建议和风险提醒
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

由于当前发布仓库不再包含内部测试与评测资产，建议至少做以下最小验证：

```bash
python -m app.main --transport stdio
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

如果命令可以正常启动并等待宿主连接，说明插件本体可运行。

### 已知限制

- GitHub 是当前版本的主要可运行 provider
- Gitee provider 仍是 MVP 状态
- Web seed provider 是轻量 HTML 抽取，不是完整搜索引擎或浏览器渲染器
- broad school retrieval 基于首批学校 profile，不保证覆盖全部高校
- 课程 profile 后续仍可继续扩充

