from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from app.schemas import ProviderSearchResult, QueryAnalysis

"""
这个文件定义所有 provider 共享的最小接口。
只要实现 search 和可选的 get_project_brief，就能被 registry 接进整条检索链路。
"""


class BaseProvider(ABC):
    name: str = "base"
    source_type: str = "web"

    @abstractmethod
    async def search(
        self,
        analysis: QueryAnalysis,
        *,
        top_k: int = 5,
        allow_domains: Optional[list[str]] = None,
        deny_domains: Optional[list[str]] = None,
    ) -> List[ProviderSearchResult]:
        # search 是 provider 的核心职责：根据 QueryAnalysis 返回候选结果。
        raise NotImplementedError

    async def get_project_brief(self, url: str) -> ProviderSearchResult | None:
        # 默认不强制 provider 实现摘要提取，拿不到时会由 service 再做兜底。
        return None
