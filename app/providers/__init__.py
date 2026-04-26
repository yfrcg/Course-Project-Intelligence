"""providers 包收纳了 GitHub、Gitee 和 Web seed 三类数据源实现。"""

from app.providers.base import BaseProvider
from app.providers.gitee import GiteeProvider
from app.providers.github import GitHubProvider
from app.providers.registry import ProviderRegistry
from app.providers.web_seed import WebSeedProvider

__all__ = [
    "BaseProvider",
    "GitHubProvider",
    "GiteeProvider",
    "ProviderRegistry",
    "WebSeedProvider",
]
