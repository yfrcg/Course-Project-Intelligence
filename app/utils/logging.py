from __future__ import annotations

import logging
import sys

"""这个文件统一项目日志格式，避免不同入口各配一套 logging。"""


def setup_logging(level: str = "INFO") -> None:
    # force=True 可以确保脚本、测试和 CLI 多次初始化时仍然以最新配置为准。
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stderr,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
