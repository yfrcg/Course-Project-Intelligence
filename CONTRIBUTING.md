# Contributing

Thanks for contributing to Course Project Intelligence MCP Server.

## Scope

This project is a learning-reference and course-project intelligence MCP server.
Contributions should improve public resource discovery, structured analysis,
provider quality, explainability, deployment, testing, and safety boundaries.

This project is not for ghostwriting assignments or generating submit-ready course work.

## Development setup

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

## Run local checks

当前精简发布仓库不包含内部 `tests/`、`eval/`、`smoke` 校验资产。

在提交改动前，至少执行以下最小检查：

```bash
python -m app.main --transport stdio
python -m app.main --transport http --host 127.0.0.1 --port 8000 --mount-path /mcp
```

确认服务能启动并等待宿主连接，再结束进程。

## Contribution guidelines

- Preserve existing MCP tool names and their input/output contracts unless a breaking change is explicitly planned.
- Keep dependencies light. Prefer stdlib or already-installed packages unless a new dependency has a clear payoff.
- Treat provider integrations as untrusted external boundaries. Fail soft, return warnings, and keep structured output stable.
- If you maintain a development fork with internal validation assets, update those checks when changing ranking, provider selection, schemas, or MCP registration behavior.
- Prefer small, composable additions over rewrites.
- Document user-visible behavior in `README.md` or `docs/` when it changes.

## Provider contributions

When adding a new provider:

- Implement the `BaseProvider` contract.
- Register it through the provider registry.
- Keep search and brief extraction independently testable.
- Return public-information summaries only. Do not add assignment-writing flows.
- Document limitations, failure modes, and any required environment variables.

See `docs/provider-development.md` for the expected workflow.

## Pull request checklist

- Minimal startup checks pass for stdio and HTTP transport
- No existing MCP tools were renamed or removed
- No provider was removed
- README/docs reflect the change
- Safety boundary remains intact
