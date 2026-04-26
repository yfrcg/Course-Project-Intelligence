# Release Checklist

本清单用于把当前仓库收束到 `v1.0-rc1` / `1.0.0rc1` 的发布候选状态。所有检查项都建立在现有接口和能力之上，不要求新增大功能。

所有文档和输出都必须继续强调：仅用于课程项目调研和学习参考，不支持直接代写、复制或抄袭提交。

## 运行验证

当前精简发布仓库不包含内部 `tests/`、`eval/`、`smoke` 校验资产。

- `python -m app.main --transport stdio`
- `python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp`
- 至少在一个真实 MCP Host 中完成接入

## MCP Tools

- `search_course_projects` 可发现
- `inspect_course_project` 可发现
- `compare_course_projects` 可发现
- `inputSchema` / `outputSchema` 可读

## 文档

- `README.md` 已更新
- `docs/tool-reference.md` 已更新
- `docs/agent-workflow.md` 已更新
- `CHANGELOG.md` 已更新

## 安全

- 所有输出保留学习参考边界
- 不输出“可直接提交”
- 不鼓励复制代码或报告
- `compare` 不把高风险仓库说成可直接复用

## Trae 手动验证

- 搜索“南开大学数据库系统大作业”
- inspect 第一个仓库
- compare 前三个仓库
- 搜索“985 高校操作系统实验”
- 搜索“算法导论笔记”并排除 `408` / `题解`

## 版本与发布文案

- 版本表述已统一为：
  - `v0.8`: Broad School Retrieval
  - `v0.9`: Course-Aware Retrieval And Analysis
  - `v1.0-rc1`: Stable Agent Workflow Release / Release Candidate
- 包版本或已有版本号位置已最小更新为 `1.0.0rc1`
- 不删除历史兼容说明

## 发布前确认

- release notes 已整理
- eval 文档已同步
- README 中没有把 Course-Aware 误写成 `v0.8`
- 没有为了通过测试或 eval 去 hardcode 某几个仓库名
