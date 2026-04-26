# Agent Workflow

版本上下文：

- `v0.8`: Broad School Retrieval
- `v0.9`: Course-Aware Retrieval And Analysis
- `v1.0-rc1`: Stable Agent Workflow Release / Release Candidate

本文档说明为什么推荐把 `search_course_projects`、`inspect_course_project`、`compare_course_projects` 串成连续工作流，以及 Agent 在 normal scope、course-aware 和 broad school scope 下应如何解释结果。

所有流程都只用于课程项目调研、学习参考、公开资料发现和技术路线比较，不支持直接代写、复制或抄袭提交。

## Three-Stage Flow

1. `search_course_projects`
   - 用来扩展候选池
   - 重点看 `repo_type`、`score`、`value_level`、`confidence_level`、`positive_evidence`、`caveat`

2. `inspect_course_project`
   - 用来深挖单个仓库是否适合当前任务
   - 重点看 `fit_for_query`、`task_fit_reason`、`detected_assets`、`suggested_usage`、`not_suitable_for`、`risk_level`

3. `compare_course_projects`
   - 用来横向比较多个候选
   - 重点看 `best_overall`、`comparison`、`recommendation`、`failed_repos`、`safety_note`

这样做的目的：
- 降低把 `collection`、`org_meta`、`exam_solution`、`generic_algorithm` 误当成主候选的风险
- 让 Agent 先找候选，再核验单仓，最后给学习建议
- 让 Host 更容易把结构化字段转成稳定解释

## Normal Scope Workflow

适用场景：
- 明确某一所学校
- 明确某门课程
- 明确想找实验、笔记、大作业、题解或资料合集

推荐链路：
1. 用户自然语言描述需求
2. 调用 `search_course_projects`
3. 选 3 到 5 个候选做 `inspect_course_project`
4. 有多个候选需要横向判断时，再调用 `compare_course_projects`

Agent 在 `search` 阶段应说明：
- 找到了哪些候选
- 哪些更像课程项目，哪些更像实验、笔记、题解或资料合集
- 为什么某些仓库值得进一步 inspect
- 哪些结果有明显限制或误用风险

Agent 在 `inspect` 阶段应说明：
- 仓库是否适合当前 query
- 仓库内部是否有 `src`、`lab`、`report`、`notes`、`sql/schema`
- 更适合参考什么，不适合参考什么
- 为什么不能把公开仓库直接当作作业提交物

Agent 在 `compare` 阶段应说明：
- 哪个仓库更适合作为主参考
- 其他仓库更适合补什么
- 是否存在明显高风险候选
- 最终建议必须保留 `safety_note`

## Course-Aware Workflow

适用场景：
- query 中显式出现课程名，如“数据库系统”“编译原理”“机器学习”
- query 只出现课程英文名、简称或弱别名，如 `DBMS`、`OS lab`、`compiler lab`、`ML project`
- 用户想比较课程专属结构，如数据库设计、调度器、AST/IR、训练评估流程

Agent 在 `search` 阶段应额外读取：
- `query_analysis.course`
- `query_analysis.course_profile_id`
- `query_analysis.detected_courses`
- `query_analysis.detected_course_ids`

解释方式：
- 若 `course_profile_id` 已稳定命中，应明确告诉用户系统当前按该课程画像在检索和评分
- 若 `detected_courses` 有多个候选，应保守表达，不把弱别名命中包装成高置信课程判断
- 若 query 只出现简称，也应解释“这是基于课程简称和结构线索推断，不代表课程官方归属”

Agent 在 `inspect` 阶段应优先解释：
- `course_profile_id`
- `course_specific_assets`
- `reference_utility`
- `suggested_usage`

示例：
- 数据库系统优先解释 `has_sql_or_schema`、`has_models`、`has_er_diagram`
- 操作系统优先解释 `has_kernel_dir`、`has_scheduler_hint`、`has_memory_hint`
- 编译原理优先解释 `has_lexer`、`has_parser`、`has_ast`、`has_ir`
- 机器学习优先解释 `has_dataset`、`has_train_script`、`has_eval_script`

Agent 在 `compare` 阶段应优先解释：
- `comparison[].course_profile_id` 是否一致
- `comparison[].course_specific_assets` 如何支撑 `best_for`
- 为什么某仓库更适合作为数据库设计 / 实验流程 / 编译前端 / 训练评估参考

Agent 不应把 course-aware 输出说成：
- “这门课的标准答案”
- “这个仓库就是你课程最适合直接复用的实现”

更合适的说法是：
- “这个仓库在当前课程画像下更适合参考某些结构点”
- “这些课程专属资产说明它适合作为学习参考，但不能直接复制提交”

## Broad Scope Workflow

适用场景：
- `985高校`
- `211高校`
- `C9高校`
- `双一流高校`
- 泛化 `高校` / `大学` 范围

推荐链路仍然是 `search -> inspect -> compare`，但 broad scope 下必须额外解释范围限制。

Agent 在 broad scope 下应先读取：
- `school_scope`
- `school_group`
- `scope_note`
- `scope_coverage`

然后再解释结果：
1. broad scope 是首批学校 profile 的分批召回，不保证覆盖全部 985 / 211 / C9 / 双一流高校
2. broad scope 不是把所有学校 alias 合并成一个 GitHub query，而是每校独立 planning、每校独立预算、统一 rerank
3. `scope_coverage.schools_covered` 只应反映真实命中的学校，不能据此虚构学校覆盖
4. 若学校证据弱、只靠歧义缩写命中或学校不在目标 group 内，应保守解释 `confidence_level`
5. broad scope 结果如果同时命中 `course_profile_id`，也只能说明“按该课程画像检索到了候选”，不代表覆盖全部同类课程仓库
6. broad scope 结果仍然只用于课程项目调研、学习参考和公开资料发现，不支持直接代写、复制或抄袭提交

推荐 broad scope 使用顺序：
1. 调用 `search_course_projects`
2. 先过滤 `org_meta`、弱学校证据候选和与 query intent 不匹配的集合型仓库
3. 优先 inspect 学校证据更强、课程证据更强、结构更完整的仓库
4. 如果需要跨学校横向比较，再调用 `compare_course_projects`

## Safety Framing

Agent 应保留的安全表述：
- 结果只用于课程项目调研、学习参考、公开资料发现和技术路线比较
- 不支持直接代写、复制或抄袭提交
- 对 `exam_solution`、`report_only`、`collection`、`org_meta`、`generic_algorithm` 要明确用途边界
- 对 `course_profile_id` 和 `course_specific_assets` 的解释也应落在“学习参考”范围内
- 高分或高置信不等于可直接提交

Agent 不应该做的事：
- 不直接复制代码
- 不生成可直接提交的作业答案
- 不隐藏来源仓库
- 不把 `collection`、`org_meta`、`exam_solution` 包装成标准课程项目答案
- 不忽略 `negative_evidence`、`risk_level`、`scope_note` 和 `safety_note`

## Host Tips

- 先用 `search_course_projects` 找 3 到 5 个候选，再调用 `inspect_course_project`
- broad scope 查询时，展示结果时建议同步显示 `school_scope`、`scope_note`、`scope_coverage`
- course-aware 查询时，展示结果时建议同步显示 `course_profile_id` 和关键 `course_specific_assets`
- 当用户提出“哪一个更适合参考某一方面”时，再调用 `compare_course_projects`
- 不要把高分或高置信直接翻译成“可直接复用”
- 始终强调仅用于课程项目调研和学习参考，不支持直接代写、复制或抄袭提交
