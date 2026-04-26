# Release Notes: v1.0-rc1

`v1.0-rc1` 是当前仓库面向正式 `1.0.0` 的发布候选版本。这个版本不引入新的大功能，而是把已经完成的 broad school retrieval、course-aware retrieval and analysis、可解释评分和 Agent workflow 收束成一个稳定、可展示、可接入、可维护的 MCP Server。

所有能力都仅用于课程项目调研和学习参考，不支持直接代写、复制或抄袭提交。

## 项目定位

面向高校计算机课程项目调研的多高校、课程感知、可解释 MCP Server。

它的目标不是给出“可直接提交的作业答案”，而是帮助 Agent 和 MCP Host：

- 检索公开课程项目、实验仓库、课程笔记和资料合集
- 分析单个仓库是否适合某个课程任务
- 比较多个候选仓库的学习参考价值
- 输出结构化证据、风险提示和安全边界

## 核心工具

- `search_course_projects`
- `inspect_course_project`
- `compare_course_projects`

## 核心能力

- 多高校范围检索
- 课程 profile
- course-aware query planning
- GitHub / Gitee / Web provider
- README / root tree enrichment
- 可解释 Source Value Evaluator
- `repo_type` 分类
- `score cap` 风险控制
- `search -> inspect -> compare` Agent workflow

## 版本演进

- `v0.8`: Broad School Retrieval
- `v0.9`: Course-Aware Retrieval And Analysis
- `v1.0-rc1`: Stable Agent Workflow Release / Release Candidate

## 当前稳定能力

`search_course_projects`

- 支持学校范围识别
- 支持 `985` / `211` / `C9` / `双一流` / `高校` 范围检索
- 支持课程 profile、course-aware query planning 和可解释评分
- 返回 `repo_type`、`score`、`value_level`、`confidence_level`、`positive_evidence`、`reference_utility`、`cap_reason`、`caveat`

`inspect_course_project`

- 支持 query 上下文
- 支持 `course_profile_id`
- 支持 `course_specific_assets`
- 保留 README / root tree enrichment 带来的结构解释能力

`compare_course_projects`

- 支持 criteria + course profile 的多仓比较
- 支持输出 `best_overall`、`comparison`、`recommendation`、`failed_repos`、`safety_note`
- 保留课程专属资产和风险解释

## 评分与风险控制

当前评分体系已经稳定为三层结构：

- `relevance_score`
- `source_value_score`
- `risk penalty + score cap`

这套体系的目标是：

- 让课程相关、结构完整、可学习参考的仓库更容易进入前列
- 让题解、组织元仓库、泛算法仓库、README-only 或学校证据弱的仓库被保守解释
- 让高分始终不等于“可直接复用”

## Agent Workflow

`v1.0-rc1` 把以下工作流作为稳定推荐路径：

```text
用户自然语言
-> search_course_projects
-> inspect_course_project
-> compare_course_projects
-> Agent 输出学习参考建议和风险提醒
```

这个工作流强调：

- 先找候选
- 再做单仓核验
- 最后做多仓比较
- 全程保留来源、证据、限制和安全边界

## 安全边界

- 仅用于课程项目调研和学习参考
- 不支持直接代写、复制或抄袭提交
- 不隐藏来源
- 不把高风险仓库包装成可直接复用

Agent 和 Host 在解释结果时，应显式保留 `risk_note`、`risk_level`、`negative_evidence`、`cap_reason` 和 `safety_note`。

## 当前验证方式

当前 GitHub 精简发布仓库只保留插件本体、文档与示例，不再包含内部 `tests/`、`eval/`、`smoke` 校验资产。

发布前建议至少执行：

```bash
python -m app.main --transport stdio
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

并在真实宿主中完成一次手动接入验证。

## 已知限制

- 学校 profile 目前是首批覆盖，不保证全量 `985` / `211`
- broad scope 是分批召回，不保证覆盖所有高校
- GitHub API 失败时会降级返回 partial result
- 课程 profile 仍可继续扩充

## 兼容性说明

- 不删除或改名已有 MCP tools
- 保持 `search_course_projects`、`inspect_course_project`、`compare_course_projects` 的兼容性
- 不要求调用方迁移到新接口
- 历史兼容说明继续保留
