# Architecture

本文描述当前 `Course Project Intelligence MCP Server` 的实际分层，而不是理想化重写版本。

## 总体分层

```text
app/main.py
  -> app/server.py
    -> app/tools/
      -> app/core/
        -> app/providers/
        -> app/ranking/
        -> app/extractors/
        -> app/utils/
```

各层职责如下：

- `server`
  - 创建 `FastMCP` 实例。
  - 注册 5 个对外 MCP tools。
  - 只关心 tool 名称、说明、structured output 和传输挂载路径。
- `tools`
  - 把 MCP tool 参数封装成 `schemas.py` 中的输入模型。
  - 调用 `CourseProjectIntelligenceService`。
  - 不直接处理 provider 细节、排序细节或网络抓取细节。
- `core`
  - 负责查询分析、结果归一化、去重、服务编排。
  - `query_analyzer.py` 负责把自然语言查询拆成学校、课程、技术词、资源词、来源提示等。
  - `normalizer.py` 负责把各 provider 的原始结果规范成统一输出结构。
  - `service.py` 负责组合 provider、ranking 和 brief/resource/compare 等业务流程。
- `providers`
  - 面向外部数据源的适配层。
  - 当前包含 `GitHubProvider`、`GiteeProvider`、`WebSeedProvider`。
  - 对 core 暴露统一的 `search()` 和 `get_project_brief()` 接口。
- `ranking`
  - `scorer.py` 负责轻量、可解释的启发式评分。
  - 不依赖复杂 reranker 或外部模型。
  - 输出分数和 explanation，供最终结果展示。
- `extractors`
  - 负责 HTML 获取后的标题、meta description、正文摘要、链接抽取等轻量解析。
  - 主要供 `WebSeedProvider` 和通用网页 brief 使用。
- `utils`
  - 放通用基础能力，如 HTTP 请求、日志、文本去重/截断/年份猜测等。
  - 应保持无业务耦合，供多个层复用。

## 请求流

以 `search_course_projects` 为例：

1. `app/server.py` 注册 MCP tool。
2. `app/tools/course_tools.py` 接收 tool 参数并构造 `SearchCourseProjectsInput`。
3. `app/core/service.py` 调用 `analyze_query()` 形成 `QueryAnalysis`。
4. service 选择合适 provider 并并行之外的顺序调用 `provider.search()`。
5. `app/ranking/scorer.py` 为每条 provider 结果打分并生成 `explanation`。
6. `app/core/normalizer.py` 统一成 `SearchResultItem`，并生成 `risk_note`、`use_case` 等字段。
7. service 汇总 `provider_status`、`warnings`、`safety_note`，返回稳定结构化结果。

## 设计原则

- MCP 对外接口稳定优先：不要轻易改 tool 名称和输入输出结构。
- provider 可替换：新增 provider 时尽量不影响 tool 层与 schema 层。
- 排序可解释：当前采用规则评分而不是黑盒模型。
- 抓取轻量：HTML 提取和网页扫描以低依赖、低复杂度为原则。
- 安全边界清晰：项目用于学习参考和公开资料情报，不用于代写或生成可提交作业。

## 当前边界

- `service.py` 是当前业务编排中心，承担结果聚合、brief 生成、路线比较、资源列表整理等职责。
- `providers` 只负责“从哪里拿”，不负责最终排序和标准化。
- `ranking` 只负责“如何给分”，不负责来源接入。
- `extractors` 只负责“如何从网页提文本/链接”，不决定结果是否入选。

这种边界保证了后续可以单独增强 provider、排名策略或部署方式，而不需要重写整个项目。
