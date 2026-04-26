# Cursor MCP Example

将当前目录下的配置样例复制到你的 Cursor MCP 配置中即可。

推荐文件：

- `python-stdio.mcp.json`: 使用 `python -m app.main --transport stdio`
- `stdio.mcp.json`: 使用已安装的 `course-intel-mcp`
- `http.mcp.json`: 连接本地 HTTP MCP 服务
- `mcp.json`: 兼容旧示例，保留为最小 stdio 配置

推荐优先使用 `python-stdio.mcp.json` 或 `stdio.mcp.json`。

`python-stdio.mcp.json` 示例：

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

如果使用 HTTP，需要先在本机启动：

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

然后在 Cursor 中导入 `http.mcp.json`。

这些配置仅用于课程项目调研和学习参考，不支持直接代写、复制或抄袭提交。
