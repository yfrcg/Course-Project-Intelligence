# Deployment

本文说明如何在不同宿主中运行当前 MCP Server。

## 前置条件

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
```

## 1. stdio

直接在当前机器上运行：

```bash
python -m app.main --transport stdio
```

安装 console script 后也可以：

```bash
course-intel-mcp --transport stdio
```

兼容性说明：

- 旧命令 `python -m app.main stdio` 与 `python -m app.main http` 仍然保留，用于兼容已有配置。

适用场景：

- Claude Code
- Cursor
- 大多数本地 generic MCP host
- 不希望单独维护 HTTP 服务时

## 2. Streamable HTTP

启动服务：

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

默认连接地址：

```text
http://127.0.0.1:8000/mcp
```

适用场景：

- 需要 URL 方式接入 MCP host
- 本地或内网已有统一代理/反向代理
- 宿主更适合连接 HTTP 端点而不是直接拉起命令

## 3. Claude Code

stdio:

```bash
claude mcp add course-project-intel -- python -m app.main --transport stdio
```

HTTP:

```bash
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
claude mcp add --transport http course-project-intel http://127.0.0.1:8000/mcp
```

参考示例：

- `examples/claude-code/README.md`

## 4. Cursor

Cursor 可直接使用 stdio 配置。

示例配置：

```json
{
  "mcpServers": {
    "course-project-intel": {
      "command": "python",
      "args": ["-m", "app.main", "--transport", "stdio"],
      "env": {
        "GITHUB_TOKEN": ""
      }
    }
  }
}
```

参考示例：

- `examples/cursor/mcp.json`
- `examples/cursor/README.md`

## 5. Generic MCP Host

stdio 示例：

```json
{
  "mcpServers": {
    "course-project-intel": {
      "command": "python",
      "args": ["-m", "app.main", "--transport", "stdio"],
      "env": {
        "GITHUB_TOKEN": ""
      }
    }
  }
}
```

HTTP 示例：

- 先启动 `python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp`
- 再在宿主中配置 `http://127.0.0.1:8000/mcp`

参考示例：

- `examples/generic-mcp-host/README.md`

## Trae IDE integration

### 1. 安装依赖

```bash
python -m venv .venv
python -m pip install -e .
```

如果你需要额外开发依赖，再安装：

```bash
python -m pip install -e ".[dev]"
```

### 2. 本地验证

```bash
python -m app.main --transport stdio
```

或：

```bash
course-intel-mcp --transport stdio
```

如果命令启动后保持等待状态，这是正常的，说明 MCP Server 正在等待宿主连接。

### 3. 在 Trae 中添加配置

- 打开 Trae IDE
- 进入 `Settings / MCP`
- 添加一个 MCP Server
- 直接粘贴 [examples/trae/python-stdio.mcp.json](../examples/trae/python-stdio.mcp.json) 中的内容

如果你已经执行过 `pip install -e .` 并希望使用 console script，也可以粘贴：

- [examples/trae/stdio.mcp.json](../examples/trae/stdio.mcp.json)

`GITHUB_TOKEN` 是可选项。为空时不影响启动，只是 GitHub provider 更容易遇到 rate limit。

### 4. 接入后推荐测试问题

- `请列出当前可用的 MCP tools。`
- `请调用 course-project-intelligence MCP 工具，搜索和“南开大学 操作系统 大作业 GitHub”相关的课程项目，并总结可参考点和风险。`

### 5. 常见问题

- `python` 命令找不到：改用绝对路径 Python，或先确认虚拟环境可执行文件在 PATH 中。
- 虚拟环境没有激活：先激活 `.venv`，再执行 `pip install -e .`。
- `app.main` 无法导入：确认命令是在仓库根目录执行，或先完成 editable install。
- `GITHUB_TOKEN` 未配置：不会影响 MCP 启动，但 GitHub 搜索更容易触发 rate limit。
- Trae 看不到 tools：先刷新或重启 MCP Server，再重新打开 Trae 的 MCP 面板。
- Windows 路径问题：优先使用绝对路径，或参考 [examples/start_mcp_stdio.bat.example](../examples/start_mcp_stdio.bat.example) 做启动脚本。

## 6. 部署注意事项

- `GITHUB_TOKEN` 可选，但未配置时 GitHub API 更容易遇到限流。
- 如果宿主通过代理访问本地 HTTP，请确保 `127.0.0.1` 和 `localhost` 被加入 `NO_PROXY`。
- 保持 `mount-path` 与宿主配置一致。
- 如果只是在本机 Agent 中接入，优先使用 `stdio`，更简单也更稳定。

## 7. 发布前检查

当前精简发布仓库不包含内部 `tests/`、`eval/`、`smoke` 校验资产。

- `python -m pip install -e .` 成功
- `python -m pip install -e ".[dev]"` 成功
- `python -m app.main --transport stdio` 能启动
- `python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp` 能启动
- 至少验证一种真实宿主接入成功，Trae 为优先验证目标
