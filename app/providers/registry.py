from __future__ import annotations

from typing import Iterable
from urllib.parse import urlparse

from app.config import Settings, get_settings
from app.providers.base import BaseProvider
from app.providers.gitee import GiteeProvider
from app.providers.github import GitHubProvider
from app.providers.web_seed import WebSeedProvider


class ProviderRegistry:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        providers: Iterable[BaseProvider] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._providers: dict[str, BaseProvider] = {}
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

        if not requested:
            return enabled

        return [
            provider
            for provider in enabled
            if self._matches_source_types(provider, requested)
        ]

    def provider_for_url(self, url: str) -> BaseProvider:
        host = urlparse(url).netloc.lower()

        if "github.com" in host and "github" in self._providers:
            return self._providers["github"]
        if self._is_enabled("gitee") and "gitee.com" in host and "gitee" in self._providers:
            return self._providers["gitee"]

        raise LookupError("Unsupported source URL for the current GitHub-only release.")
