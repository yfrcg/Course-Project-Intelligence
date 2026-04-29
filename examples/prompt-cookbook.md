# Prompt Cookbook

This cookbook helps users phrase requests so MCP hosts are more likely to select the right tool from `course-project-intelligence`.

Use all results for course-project research and learning reference only. They are not official course materials, and they must not be copied directly for submission.

## Trigger `search_course_projects`

Use this tool when the user clearly wants projects, repositories, labs, notes, assignments, reports, or public GitHub references.

- `帮我找南开大学数据库课程设计参考仓库。`
  Recommended tool: `search_course_projects`
- `有没有操作系统实验报告和源码可以参考？`
  Recommended tool: `search_course_projects`
- `帮我找 985 高校计算机网络实验 GitHub 仓库。`
  Recommended tool: `search_course_projects`
- `想找数据库系统大作业相关的公开 repo 和报告。`
  Recommended tool: `search_course_projects`
- `帮我搜高校编译原理实验相关的公开代码仓库和笔记。`
  Recommended tool: `search_course_projects`
- `Find public GitHub repositories for Nankai data structure course projects.`
  Recommended tool: `search_course_projects`
- `Search university CS repositories and notes about compiler labs.`
  Recommended tool: `search_course_projects`
- `Look for database system final assignment repositories and reports.`
  Recommended tool: `search_course_projects`

## Trigger `search_course_resources`

Use this tool when the request is broad and sounds like course materials, study materials, notes, lab materials, public learning resources, or general course information.

- `查询南开大学数据结构的课程资料。`
  Recommended tool: `search_course_resources`
- `帮我找大学编译原理的公开学习资料和实验材料。`
  Recommended tool: `search_course_resources`
- `有没有数据库课程笔记、实验资料和公开仓库？`
  Recommended tool: `search_course_resources`
- `我想找某校操作系统课的实验指导、报告模板和公开资料。`
  Recommended tool: `search_course_resources`
- `找一些高校 Java Web 课程设计资料，不一定非得是 repo。`
  Recommended tool: `search_course_resources`
- `Find university CS course materials about compiler labs on GitHub.`
  Recommended tool: `search_course_resources`
- `Look for public study resources for operating system labs.`
  Recommended tool: `search_course_resources`
- `Search course notes, reports, and lab materials for a university database course.`
  Recommended tool: `search_course_resources`

## Trigger `inspect_course_project`

Use this tool when the user already has a repository or GitHub URL and wants analysis, asset detection, or fit-for-query judgment.

- `分析这个 repo 是否适合做 Java Web 课程设计参考。`
  Recommended tool: `inspect_course_project`
- `看看第一个仓库有没有实验报告、SQL 和 schema。`
  Recommended tool: `inspect_course_project`
- `这个 GitHub 仓库适合参考什么部分？`
  Recommended tool: `inspect_course_project`
- `给你一个 GitHub URL，分析它是否适合作为数据库课程大作业参考。`
  Recommended tool: `inspect_course_project`
- `检查这个仓库里有没有 lab、src、notes 或 report 资产。`
  Recommended tool: `inspect_course_project`
- `Inspect this repository and tell me whether it is useful for compiler lab learning.`
  Recommended tool: `inspect_course_project`
- `Does this repo contain lab, src, notes, or report assets?`
  Recommended tool: `inspect_course_project`
- `Analyze whether this repository fits a database course project query.`
  Recommended tool: `inspect_course_project`

## Trigger `compare_course_projects`

Use this tool when the user wants a recommendation across multiple repositories and cares about tradeoffs.

- `比较这三个仓库哪个更适合作为数据库大作业参考。`
  Recommended tool: `compare_course_projects`
- `前三个仓库哪个更适合参考课程笔记和实验代码结构？`
  Recommended tool: `compare_course_projects`
- `帮我比较这些 repo 的报告结构和模块划分。`
  Recommended tool: `compare_course_projects`
- `比较这几个仓库，哪个更适合作为操作系统实验流程参考。`
  Recommended tool: `compare_course_projects`
- `比较前三个候选仓库，看看哪个更适合数据库设计和 schema 参考。`
  Recommended tool: `compare_course_projects`
- `Compare these three repositories for database design reference value.`
  Recommended tool: `compare_course_projects`
- `Which of the top three repos is better for operating system lab workflow?`
  Recommended tool: `compare_course_projects`
- `Compare the candidate repositories for code structure and report reference value.`
  Recommended tool: `compare_course_projects`

## Trigger `build_course_context`

Use this tool when the user wants an agent-readable evidence pack, wants to keep citation hints and risk flags, or already has known sources or prior tool outputs.

- `给我的 Agent 整理几个数据库课程设计参考资料，并说明哪些部分能参考。`
  Recommended tool: `build_course_context`
- `把这些 GitHub 链接整理成带风险提示的参考上下文。`
  Recommended tool: `build_course_context`
- `把前面的搜索结果整理成一个可以直接给 Agent 用的 context pack。`
  Recommended tool: `build_course_context`
- `Use these repository URLs to build a context pack with citation hints and safety notes.`
  Recommended tool: `build_course_context`
- `Summarize the compare result into evidence cards for an AI agent.`
  Recommended tool: `build_course_context`
- `Help me collect evidence before answering a course-project question.`
  Recommended tool: `build_course_context`

## When The Host Does Not Call A Tool

If the host keeps answering in plain chat, explicitly mention the MCP server name.

- `请使用 course-project-intelligence，帮我找南开大学数据库课程设计相关的公开仓库和笔记。`
  Recommended tool: `search_course_projects`
- `Use course-project-intelligence to search course resources about compiler labs.`
  Recommended tool: `search_course_resources`
- `Use course-project-intelligence to inspect this repository for database course reference value.`
  Recommended tool: `inspect_course_project`
- `请使用 course-project-intelligence 比较前三个仓库的代码结构和报告结构。`
  Recommended tool: `compare_course_projects`
- `Use the course-project-intelligence MCP server to search public operating system lab materials.`
  Recommended tool: `search_course_resources`
- `Use course-project-intelligence to build an agent-readable context pack from these known repository URLs.`
  Recommended tool: `build_course_context`

## Less Effective Prompts And Better Rewrites

- Not recommended: `讲讲南开大学数据结构。`
  Better: `请使用 course-project-intelligence 查询南开大学数据结构课程资料、实验仓库和课程笔记。`
- Not recommended: `给我一点数据库课的东西。`
  Better: `帮我找数据库课程的公开项目、实验报告和 GitHub 参考仓库。`
- Not recommended: `这个仓库怎么样？`
  Better: `分析这个 repo 是否适合作为 Java Web 课程设计参考，并检查有没有报告、SQL 和 src。`
- Not recommended: `这几个哪个好？`
  Better: `比较这三个仓库哪个更适合参考数据库设计、报告结构和代码结构。`
- Not recommended: `Find something about OS.`
  Better: `Use course-project-intelligence to search public operating system course materials, labs, and repositories.`
- Not recommended: `Check this GitHub link.`
  Better: `Inspect this GitHub repository and tell me whether it includes lab, notes, reports, or schema assets.`

## Safety Reminder

- Treat all results as public learning references, not official course conclusions.
- Keep the original source visible.
- Do not directly copy code, reports, or writeups for coursework submission.
