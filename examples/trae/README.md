# Trae MCP Example

Trae 已经原生支持 MCP，所以这个项目不需要额外的 “Trae 专用协议适配层”。  
对 Trae 来说，直接接入本仓库现有的 `stdio` 或 `Streamable HTTP` 即可。

推荐优先使用当前目录下的快速粘贴配置：

- [python-stdio.mcp.json](python-stdio.mcp.json)
- [stdio.mcp.json](stdio.mcp.json)
- [http.mcp.json](http.mcp.json)
- [demo.md](demo.md)

`GITHUB_TOKEN` 是可选项；如果不需要更高的 GitHub API rate limit，可以保留空字符串或从配置中删除。

## 推荐方式

### 1. 全局 stdio 接入

先安装本项目：

```bash
python -m pip install -e .
```

然后在 Trae 中打开：

`Settings > MCP > Add > Configure Manually > Raw Config (JSON)`

粘贴 [stdio.mcp.json](stdio.mcp.json) 的内容：

```json
{
  "mcpServers": {
    "course-project-intelligence": {
      "command": "course-intel-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "GITHUB_TOKEN": ""
      }
    }
  }
}
```

这种方式最简单，不需要先单独启动 HTTP 服务。

### 2. HTTP 接入

先在本机启动 MCP 服务：

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

然后在 Trae 的 Raw Config 中使用 [http.mcp.json](http.mcp.json)：

```json
{
  "mcpServers": {
    "course-project-intelligence-http": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

如果你在 Trae 所在环境里配置了系统代理，访问本地 `127.0.0.1` 时需要确保 `NO_PROXY=127.0.0.1,localhost`，否则可能出现本地 HTTP MCP 连接异常。

## 项目级接入

如果你希望只在当前项目里启用，可以在项目根目录创建：

```text
.trae/mcp.json
```

示例见 [project/.trae/mcp.json](project/.trae/mcp.json)：

```json
{
  "mcpServers": {
    "course-project-intelligence": {
      "command": "python",
      "args": ["-m", "app.main", "--transport", "stdio"],
      "env": {
        "GITHUB_TOKEN": ""
      }
    }
  }
}
```

这种方式要求 Trae 在该项目目录中启动 MCP。当前已知限制是：**Trae 的项目级 MCP 需要手动开启**。

## 在 Trae 中验证

接入成功后，可以在 Trae 里直接试：

- `用 search_course_projects 帮我找南开大学操作系统实验相关公开项目`
- `用 get_project_brief 分析这个 GitHub 仓库适合参考哪些部分`
- `用 compare_project_routes 对比两个数据库课程大作业的技术路线`
- `用 list_course_resources 列出南开大学算法导论的公开学习资料`

## 安全提醒

这个 MCP Server 只提供学习参考、项目路线分析和公开资料发现，不应用于直接生成或提交课程作业。
