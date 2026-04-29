# Host Test Prompts

These prompts are designed to verify that an MCP host can see the server, choose the right tool, and continue through the `search -> inspect -> compare` chain when needed.

Use all results for learning reference only. Do not treat them as official course materials, and do not copy code or reports for submission.

## Trae

- `请使用 course-project-intelligence，帮我找南开大学数据结构课程相关的公开项目、实验仓库和课程笔记。`
  Expected tool chain: `search_course_projects`
- `查询南开大学数据库课程资料和公开学习资源。`
  Expected tool chain: `search_course_resources`
- `先帮我找数据库系统课程相关仓库，再分析第一个仓库适合参考什么。`
  Expected tool chain: `search_course_projects -> inspect_course_project`
- `看看第一个仓库有没有报告、SQL、schema 或 src。`
  Expected tool chain: `search_course_projects -> inspect_course_project`
- `比较前三个仓库哪个更适合参考课程笔记和实验代码结构。`
  Expected tool chain: `search_course_projects -> compare_course_projects`
- `先找编译原理课程资料，再分析最相关的仓库，最后比较前三个。`
  Expected tool chain: `search_course_resources -> inspect_course_project -> compare_course_projects`
- `把这些数据库课程设计仓库整理成给 Agent 用的 evidence pack，并保留风险提示和 citation hint。`
  Expected tool chain: `build_course_context`

## Claude Code

- `Use the course-project-intelligence MCP server to search for NKU OS lab repositories.`
  Expected tool chain: `search_course_projects`
- `Use course-project-intelligence to search course materials about compiler labs.`
  Expected tool chain: `search_course_resources`
- `Search public university GitHub repositories for Java Web course projects, then inspect the top repository.`
  Expected tool chain: `search_course_projects -> inspect_course_project`
- `Inspect the first result and check whether it contains reports, SQL, schema, or src assets.`
  Expected tool chain: `search_course_projects -> inspect_course_project`
- `Compare the top three repositories for code structure and report reference value.`
  Expected tool chain: `search_course_projects -> compare_course_projects`
- `Search broad course materials for a university database course, inspect the best repository, then compare the top three.`
  Expected tool chain: `search_course_resources -> inspect_course_project -> compare_course_projects`
- `Use these known GitHub URLs to build an agent-readable context pack with risk flags and citation hints.`
  Expected tool chain: `build_course_context`

## Cursor

- `Find public GitHub repositories and notes for Nankai Database System course projects using the MCP server.`
  Expected tool chain: `search_course_projects`
- `Find public university CS course materials for operating system labs.`
  Expected tool chain: `search_course_resources`
- `Search broad compiler course materials, then inspect the first result.`
  Expected tool chain: `search_course_resources -> inspect_course_project`
- `Inspect the first repository and check whether it has lab reports or schema files.`
  Expected tool chain: `search_course_projects -> inspect_course_project`
- `Compare the first three results.`
  Expected tool chain: `search_course_projects -> compare_course_projects`
- `Use course-project-intelligence to search compiler course materials, inspect the best repo, and compare the top three.`
  Expected tool chain: `search_course_resources -> inspect_course_project -> compare_course_projects`
- `Turn the existing inspect results into a final context pack for the agent.`
  Expected tool chain: `build_course_context`

## Generic MCP Host

- `Use course-project-intelligence to search public repositories for university database course projects.`
  Expected tool chain: `search_course_projects`
- `Use course-project-intelligence to search course resources about operating system lab materials.`
  Expected tool chain: `search_course_resources`
- `Find public notes, reports, and lab materials for data structure courses.`
  Expected tool chain: `search_course_resources`
- `Inspect this GitHub repository and tell me whether it is useful for Java Web course design reference.`
  Expected tool chain: `inspect_course_project`
- `Compare these three repositories for database design and report structure.`
  Expected tool chain: `compare_course_projects`
- `Search broad compiler course materials first, inspect the strongest repo, then compare the top three candidates.`
  Expected tool chain: `search_course_resources -> inspect_course_project -> compare_course_projects`
- `Build a context pack from the compare result so the agent can answer with safety notes and citations.`
  Expected tool chain: `build_course_context`
