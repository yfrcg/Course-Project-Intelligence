# Host Test Prompts

These prompts are for the GitHub-only release.

Use all results for learning reference only. Do not treat them as official course materials, and do not copy code or reports for submission.

## Trae

- `请使用 course-project-intelligence 帮我找 GitHub 上和数据库课程设计相关的公开仓库`
  Expected tool chain: `search_course_projects`
- `请找 GitHub 上的操作系统 labs、notes 和 reports`
  Expected tool chain: `search_course_resources`
- `分析这个 GitHub 仓库适合参考什么`
  Expected tool chain: `inspect_course_project`
- `比较这几个 GitHub 仓库哪个更适合作为数据库课程设计参考`
  Expected tool chain: `compare_course_projects`
- `把这些 GitHub 仓库整理成 Evidence Pack`
  Expected tool chain: `build_course_context`
- `分析这个学校课程网页`
  Expected behavior: `unsupported_source`

## Claude Code

- `Use course-project-intelligence to search public GitHub repositories for compiler labs`
  Expected tool chain: `search_course_projects`
- `Use course-project-intelligence to search GitHub course materials for operating system labs`
  Expected tool chain: `search_course_resources`
- `Inspect this GitHub repository and tell me whether it contains report, sql, schema, or src assets`
  Expected tool chain: `inspect_course_project`
- `Compare these GitHub repositories for report structure and schema reference value`
  Expected tool chain: `compare_course_projects`
- `Build an Evidence Pack from these GitHub repository URLs`
  Expected tool chain: `build_course_context`
- `Analyze this school course page`
  Expected behavior: `unsupported_source`

## Cursor

- `Find public GitHub repositories for university database course projects`
  Expected tool chain: `search_course_projects`
- `Find GitHub-hosted course materials for computer networks labs`
  Expected tool chain: `search_course_resources`
- `Analyze this GitHub repository as a learning reference for a Java Web course project`
  Expected tool chain: `inspect_course_project`
- `Compare these GitHub repos for operating system lab workflow`
  Expected tool chain: `compare_course_projects`
- `Turn these GitHub repository URLs into an Evidence Pack with citations and risk flags`
  Expected tool chain: `build_course_context`
- `Inspect this non-GitHub URL`
  Expected behavior: `unsupported_source`

## Generic MCP Host

- `Search public GitHub repositories for university CS course projects`
  Expected tool chain: `search_course_projects`
- `Search GitHub repositories for labs, reports, assignments, and notes`
  Expected tool chain: `search_course_resources`
- `Inspect this GitHub repository URL`
  Expected tool chain: `inspect_course_project`
- `Compare these GitHub repository candidates`
  Expected tool chain: `compare_course_projects`
- `Build a final Evidence Pack from these GitHub URLs`
  Expected tool chain: `build_course_context`
