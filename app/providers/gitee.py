from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlparse

from app.providers.base import BaseProvider
from app.schemas import ProviderSearchResult, QueryAnalysis
from app.utils.text import truncate_text

"""
这个文件保留了 Gitee provider 的接口骨架。
现在它还是 MVP 占位版，但先把扩展点稳定下来，后面补实现时就不用改 core 层协议了。
"""


GITEE_MVP_TODOS = [
    "接入稳定的 Gitee 官方开放接口或授权搜索接口",
    "补充 HTML 搜索页解析并增加页面结构变更保护",
    "从学校/课程白名单种子页反向发现 Gitee 项目",
    "补充 Gitee 仓库 README 与语言信息抽取",
]


class GiteeProvider(BaseProvider):
    name = "gitee"
    source_type = "gitee"

    async def search(
        self,
        analysis: QueryAnalysis,
        *,
        top_k: int = 5,
        allow_domains: Optional[list[str]] = None,
        deny_domains: Optional[list[str]] = None,
    ) -> List[ProviderSearchResult]:
        # MVP 占位版：首版不直接抓 Gitee 搜索接口，避免绑死不稳定页面结构。
        # 后续扩展点见 GITEE_MVP_TODOS。保留 provider 接口，避免未来接入时改 core/tools。
        return []

    async def get_project_brief(self, url: str) -> ProviderSearchResult | None:
        if "gitee.com" not in (url or ""):
            return None

        # 即使还没有真正的仓库抓取逻辑，也至少把 URL 识别成一个结构化占位结果。
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        project_name = "/".join(parts[:2]) if len(parts) >= 2 else parsed.netloc or "Gitee Project"
        snippet = (
            "Gitee provider is an MVP placeholder. The URL is recognized as a public Gitee "
            "project candidate, but repository metadata and README extraction are not implemented yet."
        )

        return ProviderSearchResult(
            title=f"{project_name} (Gitee MVP placeholder)",
            url=url,
            source=self.name,
            source_type=self.source_type,
            snippet=truncate_text(snippet, 300),
            metadata={
                "mvp_placeholder": True,
                "limitations": "Search and rich repository extraction are not implemented in MVP.",
                "todo": GITEE_MVP_TODOS,
            },
        )
