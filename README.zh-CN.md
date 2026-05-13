# Course Project Intelligence MCP Server

<p align="center">
  <img src="assets/readme-hero.svg" alt="Course Project Intelligence 动态项目概览" width="100%">
</p>

<p align="center">
  <a href="README.md">English</a>
  ·
  <a href="README.zh-CN.md"><strong>中文</strong></a>
  ·
  <a href="docs/readme-showcase.html">CSS showcase</a>
  ·
  <a href="docs/readme-showcase.zh-CN.html">中文展示页</a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-2563eb?style=for-the-badge&logo=python&logoColor=white">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-FastMCP-10b981?style=for-the-badge">
  <img alt="Transport" src="https://img.shields.io/badge/stdio%20%2B%20HTTP-ready-f59e0b?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-111827?style=for-the-badge">
</p>

Course Project Intelligence 是一个面向 GitHub 的 MCP Server，用于帮助 AI Agent 发现、检查、比较并整理公开高校计算机课程项目仓库，把它们作为带来源、带风险提示的学习参考。

它适配 Trae、Claude Code、Cursor 以及其他 Model Context Protocol 客户端。服务会保留来源链接、标注风险，并避免下游 Agent 把公开仓库误认为官方课程材料。

## 项目能力

| 能力 | 输出 |
| --- | --- |
| 发现 GitHub 课程项目仓库 | 带课程、项目、实验、报告等信号的公开仓库排序结果 |
| 检查已知仓库 | README、src、report、SQL、schema、notes、lab、assignment、docs 等可用部分 |
| 比较候选仓库 | 相似点、差异点、推荐使用方式和安全提示 |
| 构建 Evidence Pack | 带来源归因、风险标记、引用提示的 Agent 可读上下文卡片 |
| 路由 Host 请求 | 稳定的 MCP 搜索、检查、比较、上下文构建工具 |

## 动态 README 说明

GitHub README 不执行自定义 JavaScript，并会限制大部分内联 CSS。因此本仓库采用兼容 GitHub 的展示方式：

- `assets/readme-hero.svg` 提供可在 README 中展示的动画 SVG
- 使用 badge 和 Markdown 表格呈现状态信息
- 通过 `README.md` 与 `README.zh-CN.md` 实现中英文文件切换
- 在 `docs/readme-showcase.html` 与 `docs/readme-showcase.zh-CN.html` 中提供完整 CSS 动效展示页

## MCP 工具

| MCP 工具 | 用途 |
| --- | --- |
| `search_course_projects` | 搜索与高校计算机课程项目、实验、作业、报告、源码、SQL/schema、笔记和课程设计相关的公开 GitHub 仓库。 |
| `search_course_resources` | 更宽泛的 GitHub 课程资源搜索入口，复用项目搜索栈。 |
| `inspect_course_project` | 检查 GitHub 仓库 URL 或 `owner/name` 标识，并识别可作为学习参考的部分。 |
| `compare_course_projects` | 比较多个公开 GitHub 仓库，判断它们作为学习参考的适用性。 |
| `build_course_context` | 从搜索、检查、比较或指定 GitHub 来源 URL 构建 Agent 可读的 Evidence Pack。 |
| `get_project_brief` | 提取轻量仓库简报，包括摘要、推断课程/学校、技术栈、项目类型和风险提示。 |
| `compare_project_routes` | 比较多个仓库的模块路径、技术选型和学习路线。 |
| `list_course_resources` | 列出指定课程相关的公开 GitHub 资源。 |

## 推荐流程

```text
GitHub search
        -> search_course_projects / search_course_resources
        -> inspect_course_project
        -> compare_course_projects
        -> build_course_context
        -> grounded agent answer
```

宽泛检索用 `search_course_resources`，已知仓库用 `inspect_course_project`，多仓库筛选用 `compare_course_projects`，最终回答前用 `build_course_context` 做带来源的上下文封装。

## 快速开始

创建并激活虚拟环境：

```bash
python -m venv .venv
```

Linux/macOS：

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

以 stdio 方式运行：

```bash
python -m app.main --transport stdio
```

以 Streamable HTTP 方式运行：

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

默认 HTTP endpoint：

```text
http://127.0.0.1:8000/mcp
```

## Host 集成

| Host | 示例 |
| --- | --- |
| Trae | [README](examples/trae/README.md), [python stdio](examples/trae/python-stdio.mcp.json), [stdio](examples/trae/stdio.mcp.json), [http](examples/trae/http.mcp.json) |
| Cursor | [README](examples/cursor/README.md), [python stdio](examples/cursor/python-stdio.mcp.json), [stdio](examples/cursor/stdio.mcp.json), [http](examples/cursor/http.mcp.json), [mcp](examples/cursor/mcp.json) |
| Claude Code | [README](examples/claude-code/README.md), [python stdio](examples/claude-code/stdio-python.txt), [stdio cli](examples/claude-code/stdio-cli.txt), [http](examples/claude-code/http.txt) |

## 文档

- [工具路由指南](docs/tool-routing-guide.md)
- [Agent Context Pack](docs/agent-context-pack.md)
- [Agent Workflow](docs/agent-workflow.md)
- [路由诊断](docs/routing-diagnostics.md)
- [工具参考](docs/tool-reference.md)
- [架构说明](docs/architecture.md)
- [Prompt Cookbook](examples/prompt-cookbook.md)
- [Host 测试提示](examples/host-test-prompts.md)
- [评测说明](eval/README.md)

## 验证

```bash
python -m pytest -q
python eval/run_eval.py
python eval/run_agent_context_eval.py
python eval/run_workflow_eval.py
python scripts/smoke_stdio.py
python smoke_test.py
```

PowerShell：

```powershell
$env:PYTHONPATH='.'
python eval/run_eval.py
python eval/run_agent_context_eval.py
python eval/run_workflow_eval.py
```

## 安全边界

- 所有结果都应视为公开 GitHub 学习参考。
- 不要把发现的仓库描述为官方课程材料。
- 在下游回答中保留来源 URL。
- 不要直接复制代码、报告、实验、作业或笔记用于提交。
- 本服务用于研究、比较和带来源的上下文构建，不用于生成可直接提交的课程作业。
