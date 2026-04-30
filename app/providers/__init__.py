"""Providers package with GitHub as the active release provider and others retained for future extension."""

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
