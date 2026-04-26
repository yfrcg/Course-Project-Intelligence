from __future__ import annotations

import argparse
from collections.abc import Sequence

import uvicorn

from app.config import get_settings
from app.server import create_mcp_server
from app.utils.logging import setup_logging

"""
这个文件是项目命令行入口。
它负责解析启动参数，并决定当前进程走 stdio 模式还是 HTTP 模式。
"""


def normalize_mount_path(path: str) -> str:
    # 这里统一把挂载路径整理成 `/mcp` 这种格式，避免前后端对路径理解不一致。
    path = (path or "/mcp").strip()
    if not path.startswith("/"):
        path = f"/{path}"
    if len(path) > 1:
        path = path.rstrip("/")
    return path


def run_stdio() -> None:
    # stdio 模式通常给 MCP host 直接拉起，流程只需要初始化日志并启动 server。
    settings = get_settings()
    setup_logging(settings.log_level)

    mcp = create_mcp_server()
    mcp.run()


def run_http(host: str, port: int, mount_path: str) -> None:
    # HTTP 模式下要把 FastMCP 包成 ASGI 应用，再交给 uvicorn 托管。
    settings = get_settings()
    setup_logging(settings.log_level)

    endpoint_path = normalize_mount_path(mount_path)
    mcp = create_mcp_server(streamable_http_path=endpoint_path)
    app = mcp.streamable_http_app()

    uvicorn.run(app, host=host, port=port, log_level=settings.log_level.lower())


def build_parser() -> argparse.ArgumentParser:
    # 这里同时保留新参数和旧位置参数，兼容已有脚本调用方式。
    parser = argparse.ArgumentParser(
        prog="course-intel-mcp",
        description="Course Project Intelligence MCP Server",
    )
    parser.add_argument(
        "legacy_transport",
        nargs="?",
        choices=("stdio", "http"),
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        help="Transport to run: stdio or http.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP host. Default: 127.0.0.1")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port. Default: 8000")
    parser.add_argument(
        "--mount-path",
        default="/mcp",
        help="Streamable HTTP endpoint path. Default: /mcp",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    # 如果新旧两套写法同时出现，而且值不同，就直接报错，避免静默走错模式。
    if args.transport and args.legacy_transport and args.transport != args.legacy_transport:
        parser.error(
            f"Conflicting transport values: positional `{args.legacy_transport}` and "
            f"`--transport {args.transport}`."
        )

    # 统一收口成一个 transport 字段，后面的主流程就不用关心用户是哪种写法了。
    args.transport = args.transport or args.legacy_transport
    if not args.transport:
        parser.error("Transport is required. Use `--transport stdio` or `--transport http`.")

    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    # 入口只做分发，真正的启动细节交给各自的 run_* 函数处理。
    if args.transport == "stdio":
        run_stdio()
        return

    run_http(args.host, args.port, args.mount_path)


def cli(argv: Sequence[str] | None = None) -> None:
    main(argv)


if __name__ == "__main__":
    main()
