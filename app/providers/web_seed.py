from __future__ import annotations

from typing import List, Optional
from urllib.parse import urlparse

from app.config import get_settings
from app.core.query_analyzer import build_search_query
from app.core.retrieval_profiles import build_relevance_terms, build_seed_sites
from app.extractors.web import (
    ExtractedLink,
    extract_link_items,
    extract_meta_description,
    extract_text_content,
    extract_title,
    fetch_html,
)
from app.providers.base import BaseProvider
from app.schemas import ProviderSearchResult, QueryAnalysis
from app.core.vocabulary import term_in_text
from app.utils.logging import get_logger
from app.utils.text import normalize_url_key, truncate_text


logger = get_logger(__name__)

"""
这个文件实现 Web seed provider。
它不依赖搜索引擎，而是从一组种子站点出发，顺着页面链接去发现公开资源。
"""


class WebSeedProvider(BaseProvider):
    name = "web_seed"
    source_type = "web"
    non_html_extensions = (
        ".7z",
        ".avi",
        ".doc",
        ".docx",
        ".gif",
        ".gz",
        ".jpg",
        ".jpeg",
        ".mp4",
        ".pdf",
        ".png",
        ".ppt",
        ".pptx",
        ".rar",
        ".tar",
        ".xls",
        ".xlsx",
        ".zip",
    )

    def __init__(self) -> None:
        self.settings = get_settings()

    def _domain_allowed(
        self,
        url: str,
        allow_domains: Optional[list[str]],
        deny_domains: Optional[list[str]],
    ) -> bool:
        host = urlparse(url).netloc.lower()

        if deny_domains:
            for domain in deny_domains:
                if domain.lower() in host:
                    return False

        if allow_domains:
            return any(domain.lower() in host for domain in allow_domains)

        return True

    def _looks_relevant(self, text: str, analysis: QueryAnalysis) -> bool:
        # Web seed 的相关性判断要足够宽松，否则很多入口页会在第一轮就被过滤掉。
        keywords = build_relevance_terms(analysis)
        if not keywords:
            return True

        hit_count = sum(1 for keyword in keywords if term_in_text(text, keyword))
        return hit_count >= 1

    def _should_fetch_target(self, url: str) -> bool:
        # 对明显的二进制文件链接不做正文抓取，避免浪费网络请求。
        path = urlparse(url).path.lower()
        return not path.endswith(self.non_html_extensions)

    def _seed_link_to_result(
        self,
        link: ExtractedLink,
        seed_url: str,
        *,
        title: str,
        snippet: str,
        metadata_extra: Optional[dict] = None,
    ) -> ProviderSearchResult:
        # 每个链接都补上它是从哪个 seed 页发现的，后面 service 会用这个做多样性控制。
        metadata = {
            "seed_url": seed_url,
            "anchor_text": link.text,
        }
        if metadata_extra:
            metadata.update(metadata_extra)

        return ProviderSearchResult(
            title=title or link.text or link.url,
            url=link.url,
            source=self.name,
            source_type=self.source_type,
            snippet=truncate_text(snippet or f"Discovered from seed site: {seed_url}", 320),
            metadata=metadata,
        )

    def _unique_result_count(self, items: List[ProviderSearchResult]) -> int:
        seen = set()
        for item in items:
            seen.add(normalize_url_key(item.url))
        return len(seen)

    async def _scan_seed(
        self,
        seed_url: str,
        analysis: QueryAnalysis,
        *,
        allow_domains: Optional[list[str]],
        deny_domains: Optional[list[str]],
        max_links: int = 20,
        results_limit: int | None = None,
    ) -> List[ProviderSearchResult]:
        try:
            html = await fetch_html(seed_url)
        except Exception as exc:
            logger.warning("Web seed fetch failed for %s: %s", seed_url, exc)
            return []

        links = extract_link_items(html, seed_url)[:max_links]
        results: List[ProviderSearchResult] = []

        search_text = build_search_query(analysis)
        seed_title = extract_title(html) or seed_url
        seed_snippet = extract_meta_description(html) or extract_text_content(html, max_len=600)

        if self._looks_relevant(f"{seed_title} {seed_snippet} {seed_url}", analysis):
            # seed 页本身如果就很相关，也把它当成一个候选结果返回。
            results.append(
                self._seed_link_to_result(
                    ExtractedLink(url=seed_url, text=seed_title),
                    seed_url,
                    title=seed_title,
                    snippet=seed_snippet or f"Seed index page: {seed_url}",
                    metadata_extra={"is_seed_index": True},
                )
            )

        for link in links:
            if results_limit is not None and len(results) >= results_limit:
                break

            if not self._domain_allowed(link.url, allow_domains, deny_domains):
                continue

            text_basis = f"{link.url} {link.text} {search_text}"
            if not self._looks_relevant(text_basis, analysis):
                continue

            title = link.text or link.url
            snippet = f"Discovered from seed site: {seed_url}"

            # 对相关链接再做一次轻量抓取，这样返回结果里会有更像样的标题和摘要。
            if self._should_fetch_target(link.url):
                try:
                    target_html = await fetch_html(link.url)
                    extracted_title = extract_title(target_html)
                    meta_description = extract_meta_description(target_html)
                    extracted_text = extract_text_content(target_html, max_len=600)
                    if extracted_title:
                        title = extracted_title
                    if meta_description:
                        snippet = meta_description
                    elif extracted_text:
                        snippet = truncate_text(extracted_text, 320)
                except Exception as exc:
                    logger.debug("Web target fetch failed for %s: %s", link.url, exc)
            else:
                snippet = f"{snippet}; anchor={link.text or 'resource link'}"

            if not self._looks_relevant(f"{title} {snippet} {link.url}", analysis):
                continue

            results.append(
                self._seed_link_to_result(
                    link,
                    seed_url,
                    title=title,
                    snippet=snippet,
                )
            )

        return results

    async def search(
        self,
        analysis: QueryAnalysis,
        *,
        top_k: int = 5,
        allow_domains: Optional[list[str]] = None,
        deny_domains: Optional[list[str]] = None,
    ) -> List[ProviderSearchResult]:
        if not self.settings.enable_web_seed:
            return []

        # allow_domains 在 web_seed 里有双重含义：既是白名单，也可以直接当种子域名集合。
        seed_candidates = list(allow_domains or self.settings.seed_sites)
        seeds = (
            seed_candidates
            if allow_domains
            else build_seed_sites(analysis, seed_candidates)
        )

        normalized_seeds = []
        for item in seeds[: self.settings.max_seed_sites]:
            if item.startswith("http://") or item.startswith("https://"):
                normalized_seeds.append(item)
            else:
                normalized_seeds.append(f"https://{item}")

        results: List[ProviderSearchResult] = []
        per_seed = max(3, min(top_k, 10))
        per_seed_result_limit = max(4, min(top_k, 6))

        min_seed_passes = min(5, len(normalized_seeds))

        for index, seed in enumerate(normalized_seeds, start=1):
            results.extend(
                await self._scan_seed(
                    seed,
                    analysis,
                    allow_domains=allow_domains,
                    deny_domains=deny_domains,
                    max_links=min(self.settings.max_links_per_seed, max(8, per_seed * 2)),
                    results_limit=per_seed_result_limit,
                )
            )
            if (
                index >= min_seed_passes
                and self._unique_result_count(results) >= max(top_k + 3, top_k * 2)
            ):
                # 已经扫出足够多的去重候选时，就提前停，避免把所有 seed 都刷一遍。
                break

        # 最后再按 URL 去重一次，避免不同种子页指向同一个资源。
        deduped: List[ProviderSearchResult] = []
        seen = set()
        for item in results:
            key = normalize_url_key(item.url)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        return deduped[:top_k]

    async def get_project_brief(self, url: str) -> ProviderSearchResult | None:
        try:
            html = await fetch_html(url)
        except Exception as exc:
            logger.warning("Web brief fetch failed for %s: %s", url, exc)
            return None

        title = extract_title(html) or url
        text = extract_text_content(html, max_len=1000)

        # web 摘要比较朴素，只保留标题和正文前几百字作为 brief。
        return ProviderSearchResult(
            title=title,
            url=url,
            source=self.name,
            source_type=self.source_type,
            snippet=text,
            metadata={},
        )
