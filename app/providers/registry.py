from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from app.config import Settings, get_settings
from app.providers.base import BaseProvider
from app.providers.gitee import GiteeProvider
from app.providers.github import GitHubProvider
from app.providers.web_seed import WebSeedProvider

"""
这个文件负责管理 provider 注册表。
service 层不会直接 new 某个 provider，而是统一从这里取可用 provider 和 URL 路由结果。
"""


class ProviderRegistry:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        providers: Iterable[BaseProvider] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._providers: dict[str, BaseProvider] = {}

        # 允许外部注入 provider，方便测试用 fake provider 替换真实实现。
        initial_providers = list(providers) if providers is not None else self._build_default_providers()
        for provider in initial_providers:
            self.register(provider)

    def _build_default_providers(self) -> list[BaseProvider]:
        return [
            GitHubProvider(),
            GiteeProvider(),
            WebSeedProvider(),
        ]

    def register(self, provider: BaseProvider) -> BaseProvider:
        self._providers[provider.name] = provider
        return provider

    def set_provider(self, name: str, provider: BaseProvider) -> BaseProvider:
        self._providers[name] = provider
        return provider

    def get(self, name: str) -> BaseProvider:
        return self._providers[name]

    def get_optional(self, name: str) -> BaseProvider | None:
        return self._providers.get(name)

    def all(self) -> list[BaseProvider]:
        return list(self._providers.values())

    def _is_enabled(self, provider_name: str) -> bool:
        if provider_name == "github":
            return self.settings.enable_github
        if provider_name == "gitee":
            return self.settings.enable_gitee
        if provider_name == "web_seed":
            return self.settings.enable_web_seed
        return True

    def enabled_providers(self) -> list[BaseProvider]:
        return [
            provider
            for name, provider in self._providers.items()
            if self._is_enabled(name)
        ]

    def _matches_source_types(self, provider: BaseProvider, requested: set[str]) -> bool:
        # web_seed 对外通常按 `web` 暴露，所以这里补一个别名映射。
        provider_tokens = {
            provider.name.lower(),
            (provider.source_type or "").lower(),
        }
        if provider.name == "web_seed":
            provider_tokens.add("web")

        return bool(requested & {token for token in provider_tokens if token})

    def select_search_providers(self, source_types: list[str] | None) -> list[BaseProvider]:
        enabled = self.enabled_providers()
        requested = {
            source_type.lower()
            for source_type in (source_types or [])
            if source_type
        }

        # 没指定来源时，默认返回所有启用状态下的 provider。
        if not requested:
            return enabled

        return [
            provider
            for provider in enabled
            if self._matches_source_types(provider, requested)
        ]

    def provider_for_url(self, url: str) -> BaseProvider:
        host = urlparse(url).netloc.lower()

        # 这里按 URL host 选最合适的 provider，方便 `get_project_brief` 直接走专属实现。
        if "github.com" in host and "github" in self._providers:
            return self._providers["github"]
        if "gitee.com" in host and "gitee" in self._providers:
            return self._providers["gitee"]

        web_seed = self._providers.get("web_seed")
        if web_seed is not None:
            return web_seed

        if self._providers:
            return next(iter(self._providers.values()))

        raise LookupError("No providers are registered.")
