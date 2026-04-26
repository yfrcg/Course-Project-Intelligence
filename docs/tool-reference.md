# Tool Reference

版本上下文：

- `v0.8`: Broad School Retrieval
- `v0.9`: Course-Aware Retrieval And Analysis
- `v1.0-rc1`: Stable Agent Workflow Release / Release Candidate

本文档面向 Trae、Cursor、Claude Code 等 MCP Host，说明 `search_course_projects`、`inspect_course_project`、`compare_course_projects` 的输入 schema、输出 schema 和关键字段语义。

所有工具输出都仅用于课程项目调研和学习参考，不支持直接代写、复制或抄袭提交。

## search_course_projects

### 输入 schema

```json
{
  "query": "string, required",
  "school": "string | null",
  "course": "string | null",
  "source_types": ["string"],
  "top_k": "integer, 1..20",
  "freshness": "string | null",
  "allow_domains": ["string"],
  "deny_domains": ["string"]
}
```

### 输出 schema

```json
{
  "query_analysis": {
    "raw_query": "string",
    "school": "string | null",
    "school_id": "string | null",
    "detected_schools": ["string"],
    "detected_school_ids": ["string"],
    "school_detection": ["object"],
    "school_scope": "string",
    "scope_evidence": ["string"],
    "course": "string | null",
    "course_profile_id": "string | null",
    "detected_courses": ["string"],
    "detected_course_ids": ["string"],
    "project_keywords": ["string"],
    "tech_keywords": ["string"],
    "resource_keywords": ["string"],
    "year_hint": "integer | null",
    "source_types": ["string"],
    "source_type_reasons": ["string"]
  },
  "school_scope": "string | null",
  "school_group": "string | null",
  "scope_note": "string | null",
  "scope_coverage": "object | null",
  "total_found": "integer",
  "results": [
    {
      "title": "string",
      "url": "string",
      "source": "string",
      "source_type": "string",
      "repo": "string | null",
      "snippet": "string",
      "school": "string | null",
      "school_id": "string | null",
      "course": "string | null",
      "tech_tags": ["string"],
      "year": "integer | null",
      "confidence": "number",
      "score": "number | null",
      "use_case": "string",
      "risk_note": "string",
      "explanation": "string",
      "description": "string | null",
      "language": "string | null",
      "updated_at": "string | null",
      "stars": "integer | null",
      "intent": "string | null",
      "repo_type": "string | null",
      "value_level": "string | null",
      "confidence_level": "string | null",
      "why_recommended": "string | null",
      "positive_evidence": ["string"],
      "negative_evidence": ["string"],
      "reference_utility": ["string"],
      "cap_reason": "string | null",
      "caveat": "string | null",
      "matched_school": "string | null",
      "school_evidence": ["string"],
      "school_match_strength": "string | null",
      "matched_school_aliases": ["string"],
      "matched_course": "string | null",
      "matched_intent": "string | null",
      "source_provider": "string | null",
      "metadata": "object"
    }
  ],
  "provider_status": "object",
  "warnings": ["string"],
  "safety_note": "string"
}
```

### Broad school scope behavior

`search_course_projects` 现在支持以下 school scope：
- `specific_school`
- `multiple_schools`
- `project_985`
- `project_211`
- `c9`
- `double_first_class`
- `broad_university`
- `none`

broad scope 查询示例：

```json
{
  "query": "985高校 操作系统实验 github",
  "top_k": 10
}
```

broad scope 下的执行方式：
- 系统按学校 profile 分批召回，不会把全部学校 alias 合并成一个 GitHub query
- 默认最多选择 10 所学校，每校候选预算 2，总候选上限 30
- 查询命中范围来自首批学校 profile，不保证穷尽全部 985 / 211 / C9 / 双一流高校
- 最终结果会统一 enrichment、统一 scorer、统一 rerank，并保留 `scope_note` / `scope_coverage`
- 若学校证据不足、只靠歧义缩写命中或学校不在目标 group 内，`confidence_level` 会降低

## inspect_course_project

### 输入 schema

```json
{
  "repo": "string, required, owner/name",
  "query": "string | null",
  "include_readme": "boolean",
  "include_tree": "boolean"
}
```

### 输出 schema

```json
{
  "repo": "string",
  "url": "string | null",
  "source_provider": "string | null",
  "repo_type": "string",
  "school": "string | null",
  "school_id": "string | null",
  "course": "string | null",
  "course_profile_id": "string | null",
  "intent": "string | null",
  "score": "number | null",
  "value_level": "string | null",
  "confidence_level": "string | null",
  "fit_for_query": "string",
  "task_fit_reason": "string | null",
  "not_suitable_for": ["string"],
  "suggested_usage": ["string"],
  "risk_level": "string",
  "language": "string | null",
  "updated_at": "string | null",
  "stars": "integer | null",
  "error": "string | null",
  "readme_summary": "string | null",
  "root_tree": ["string"],
  "detected_assets": "object<string, boolean>",
  "course_specific_assets": "object<string, boolean>",
  "reference_utility": ["string"],
  "risk_note": "string | null",
  "suggested_next_steps": ["string"],
  "reference_suggestions": ["string"],
  "safety_note": "string",
  "why_recommended": "string | null",
  "positive_evidence": ["string"],
  "negative_evidence": ["string"],
  "debug": "object"
}
```

## compare_course_projects

### 输入 schema

```json
{
  "repos": ["string, owner/name, min 2, max 5"],
  "query": "string | null",
  "criteria": ["string"],
  "include_details": "boolean"
}
```

### 输出 schema

```json
{
  "query": "string | null",
  "criteria": ["string"],
  "best_overall": "string | null",
  "summary": "string",
  "comparison": [
    {
      "repo": "string",
      "url": "string | null",
      "repo_type": "string",
      "school": "string | null",
      "course": "string | null",
      "course_profile_id": "string | null",
      "intent": "string | null",
      "score": "number | null",
      "value_level": "string | null",
      "confidence_level": "string | null",
      "fit_for_query": "string",
      "best_for": ["string"],
      "weaknesses": ["string"],
      "risk_level": "string",
      "reason": "string",
      "reference_utility": ["string"],
      "suggested_usage": ["string"],
      "not_suitable_for": ["string"],
      "detected_assets": "object<string, boolean>",
      "course_specific_assets": "object<string, boolean>"
    }
  ],
  "failed_repos": [
    {
      "repo": "string",
      "error": "string"
    }
  ],
  "recommendation": "string",
  "safety_note": "string"
}
```

## 重要字段解释

`repo_type`

- 仓库类型判断，用于区分课程项目、实验、笔记、题解、合集或组织元仓库
- 宿主不应把 `repo_type=exam_solution`、`org_meta`、`generic_algorithm` 解释成“可直接复用的课程项目”

`score`

- 可解释综合分
- 用于排序和比较，不等于“可以直接使用”

`value_level`

- 对学习参考价值的等级总结
- 常用于把候选粗分成高价值、中等价值、低价值

`confidence`

- 结果级数值置信度，常见于 `search_course_projects` 单条结果
- 表示当前判断的把握度，不表示可提交性

`confidence_level`

- 置信度的离散等级表达
- 适合 Host 做摘要或 UI 标签展示

`fit_for_query`

- 当前仓库对用户任务上下文的匹配度
- 典型值为 `high`、`medium`、`low`、`unknown`

`course_profile_id`

- 课程画像 ID
- 用于把 query、单仓分析和多仓比较对齐到同一门课程的结构化语义
- 常见值包括 `database_system`、`operating_system`、`compiler`、`machine_learning`

`risk_level`

- 风险等级
- 典型高风险场景包括题解仓库、组织元仓库、泛算法仓库，以及与当前 query 明显不匹配的候选

`reference_utility`

- 建议如何把该仓库用于学习参考
- 例如参考数据库设计、目录结构、实验组织方式、README 运行说明

`detected_assets`

- 从 README 和根目录结构提取出的资产信号
- 例如是否存在 `src`、`lab`、`report`、`notes`、`sql/schema`

`course_specific_assets`

- 课程专属资产信号
- 用于区分“数据库设计是否充分”“操作系统是否有 kernel/scheduler 线索”“编译项目是否有 lexer/parser/AST/IR”“机器学习项目是否有 dataset/train/eval”
- 适合被 Host 直接用来解释“这个仓库适合参考什么”

`positive_evidence`

- 支持当前推荐结论的正向证据
- Agent 应优先引用这些证据解释“为什么推荐”

`negative_evidence`

- 不利于当前推荐结论的反向证据
- Agent 应同时展示，避免过度乐观

`cap_reason`

- 分数封顶原因
- 常见于合集、题解、README-only、学校命中弱等场景

`caveat`

- 使用注意事项
- 适合在 Agent 总结里作为限制条件输出

`safety_note`

- 全局安全提醒
- 宿主应保留或转述这条提醒，强调仅用于课程项目调研和学习参考，不支持直接代写、复制或抄袭提交

## repo_type 枚举

`course_project`

- 更像公开课程项目或大作业仓库

`lab_code`

- 更像实验代码或实验实现

`notes`

- 更像课程笔记、讲义整理、知识点梳理

`report_only`

- 更偏报告、文档或总结，代码结构可能不完整

`exam_solution`

- 更偏题解、答案、真题整理
- 风险通常较高，只适合知识点核对

`collection`

- 多课程、多资料入口或资源合集
- 适合作为扩展检索入口，不适合作为单一实现模板

`org_meta`

- 组织主页、`.github` profile、社区元信息仓库
- 不应当作课程项目主体

`generic_algorithm`

- 通用算法/刷题仓库
- 可能对基础知识有帮助，但不等于特定学校课程项目

`unknown`

- 证据不足，暂时无法可靠归类

## Course-Aware 字段

`query_analysis.course_profile_id`

- query 级课程画像识别结果
- 由课程中文名、英文名、简称、弱别名和结构线索共同决定

`query_analysis.detected_courses`

- 检测到的课程候选名称列表
- 用于展示课程别名命中或课程歧义情况

`query_analysis.detected_course_ids`

- 与 `detected_courses` 对应的稳定课程画像 ID 列表
- 适合 Host 做后续流程状态传递

`inspect_course_project.course_profile_id`

- 单仓分析阶段使用的课程画像 ID
- 优先由 `query` 提供上下文，没有时会回退到仓库自身识别

`compare_course_projects.comparison[].course_profile_id`

- 多仓比较阶段的课程画像 ID
- 便于确认 compare 是否真的围绕同一门课程在做判断

## Course-Specific Assets 示例

数据库系统：

- `has_sql_or_schema`
- `has_models`
- `has_er_diagram`

操作系统：

- `has_kernel_dir`
- `has_ucore`
- `has_scheduler_hint`
- `has_memory_hint`
- `has_file_system_hint`

编译原理：

- `has_lexer`
- `has_parser`
- `has_ast`
- `has_ir`
- `has_llvm`
- `has_codegen`

算法导论：

- `has_chapter_notes`
- `has_dp_notes`
- `has_graph_notes`
- `has_complexity_notes`

机器学习：

- `has_notebook`
- `has_dataset`
- `has_train_script`
- `has_eval_script`
- `has_model_dir`

## 等级字段含义

`value_level`

- `high`: 课程相关性和结构证据都较强，适合作为学习参考
- `medium`: 有参考价值，但需要交叉验证，不能单独依赖
- `low`: 参考价值有限，通常只适合作为补充线索

`confidence_level`

- `high`: 学校、课程、意图或结构证据较明确
- `medium`: 有一定证据，但仍存在歧义
- `low`: 证据较弱，推断不稳定

`risk_level`

- `low`: 更偏笔记或低误用风险资料
- `medium`: 可以参考，但需要显式提醒不要直接复用
- `high`: 误用风险高，或与当前任务不匹配，Agent 应更谨慎解释

## Host 接入建议

- 展示结果时优先保留 `why_recommended`、`positive_evidence`、`negative_evidence`、`reference_utility`、`risk_level`、`safety_note`
- 不要把高分直接解释成“可直接提交”
- 不要隐去来源仓库
- 对 `exam_solution`、`report_only`、`collection`、`org_meta`、`generic_algorithm` 应保守表达用途边界
