# Trae Demo

版本上下文：

- `v0.8`: Broad School Retrieval
- `v0.9`: Course-Aware Retrieval And Analysis
- `v1.0-rc1`: Stable Agent Workflow Release / Release Candidate

以下 demo 用于展示本 MCP Server 在 Trae 中的典型使用方式。所有示例都只用于课程项目调研、学习参考、公开资料发现和技术路线比较，不支持直接代写、复制或抄袭提交。

## Demo 1: 数据库系统大作业

### Search Query

```json
{
  "query": "南开大学 数据库系统 大作业 github",
  "top_k": 5
}
```

关注点：
- `repo_type` 是否更像 `course_project`
- `positive_evidence` 是否出现课程名、学校名、`src` / `sql` / `report` / `README`
- `query_analysis.course_profile_id` 是否稳定命中 `database_system`
- `reference_utility` 是否明确提到数据库设计、模块划分、运行说明
- `risk_note` 是否继续强调不能直接复用代码或报告

### Inspect Repo

```json
{
  "repo": "lazy-forever/CourseSelectSystem",
  "query": "南开大学 数据库系统 大作业",
  "include_readme": true,
  "include_tree": true
}
```

关注点：
- `fit_for_query`
- `course_profile_id`
- `detected_assets.has_sql_or_schema`
- `course_specific_assets.has_models`
- `course_specific_assets.has_er_diagram`
- `detected_assets.has_src`
- `suggested_usage`
- `not_suitable_for`

### Compare Repos

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

预期返回片段示例：

```json
{
  "course_profile_id": "database_system",
  "course_specific_assets": {
    "has_sql_or_schema": true,
    "has_models": true,
    "has_er_diagram": true
  }
}
```

## Demo 2: 操作系统实验

### Search Query

```json
{
  "query": "南开大学 操作系统 实验 github",
  "top_k": 5
}
```

关注点：
- `repo_type` 是否更像 `lab_code`
- `positive_evidence` 是否出现 `lab`、`labs`、`kernel`、`src`
- `query_analysis.course_profile_id` 是否命中 `operating_system`
- `detected_assets.has_lab`
- 是否把 `exam_solution` / `report_only` / `collection` 降到主推荐之后

### Inspect Repo

```json
{
  "repo": "lazy-forever/NKU_OS_24fall",
  "query": "南开大学 操作系统 实验",
  "include_readme": true,
  "include_tree": true
}
```

关注点：
- `course_profile_id`
- `course_specific_assets.has_kernel_dir`
- `course_specific_assets.has_scheduler_hint`
- `course_specific_assets.has_memory_hint`
- `reference_utility` 是否更偏实验流程、内核模块和调度/内存管理

## Demo 3: 算法导论笔记

### Search Query

```json
{
  "query": "南开大学 算法导论 笔记 github",
  "top_k": 5
}
```

关注点：
- 优先看 `repo_type=notes`
- `query_analysis.course_profile_id` 是否命中 `algorithms`
- 结合 `negative_evidence` 识别是否混入 408、题解或泛算法仓库
- `reference_utility` 是否更偏向知识点整理，而不是项目实现
- `risk_note` 是否提醒不要把题解仓库误判为课程笔记

## Demo 4: 编译原理 Course-Aware Inspect

### Inspect Repo

```json
{
  "repo": "pku-team/compiler-lab",
  "query": "北京大学 编译原理 lab github",
  "include_readme": true,
  "include_tree": true
}
```

关注点：
- `course_profile_id` 是否为 `compiler`
- `course_specific_assets` 是否出现 `has_lexer`、`has_parser`、`has_ast`、`has_ir`
- `reference_utility` 是否明确提到词法分析、语法分析、AST/IR 或 LLVM/codegen
- `safety_note` 是否继续强调只能学习参考，不能直接复用实现

预期返回片段示例：

```json
{
  "course_profile_id": "compiler",
  "course_specific_assets": {
    "has_lexer": true,
    "has_parser": true,
    "has_ast": true,
    "has_ir": true
  }
}
```

## Demo 5: Broad School Retrieval

### Search Query

```json
{
  "query": "985高校 操作系统实验 github",
  "top_k": 10
}
```

关注点：
- 顶层 `school_scope` 是否为 `project_985`
- 是否返回 `school_group`、`scope_note`、`scope_coverage`
- `scope_coverage.schools_covered` 是否只反映真实召回命中的学校
- 前 10 个结果里是否有 school coverage 多样化，而不是同一学校完全霸榜
- 若学校证据弱、只靠歧义缩写命中或不在目标 group 内，`confidence_level` 是否被压低

### Inspect Repo

```json
{
  "repo": "thu-team/os-lab",
  "query": "985高校 操作系统实验 github",
  "include_readme": true,
  "include_tree": true
}
```

关注点：
- `fit_for_query` 是否建立在明确学校证据、课程证据和结构证据之上
- `task_fit_reason` 是否解释了 broad scope 下为什么值得参考
- `not_suitable_for` 与 `risk_note` 是否继续强调不能直接代写、复制或抄袭提交

### Expected Assistant Style Response

```text
这是一个 broad school retrieval 查询。结果来自首批 985 高校 profile 的分批召回，不保证覆盖全部 985 高校；我会先看 school_scope、scope_note 和 scope_coverage，再优先检查学校证据更强、课程证据更强、repo_type 更贴近“操作系统实验”的候选。若某个结果只靠缩写命中、缺少明确学校证据，我会把它视为低置信参考而不是主推荐。以下内容仅用于课程项目调研和学习参考，不支持直接代写、复制或抄袭提交。
```
