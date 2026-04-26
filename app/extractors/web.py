from __future__ import annotations

from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.utils.http import fetch_text
from app.utils.text import normalize_url_key, normalize_whitespace, truncate_text

"""
这个文件提供一组轻量网页提取函数。
Web seed provider 会用它来抽标题、正文摘要和链接，而不会把 HTML 解析逻辑散落到 provider 里。
"""


async def fetch_html(url: str) -> str:
    return await fetch_text(url)


@dataclass(frozen=True)
class ExtractedLink:
    # 这里把链接地址和锚文本绑在一起，后面 provider 可以同时利用这两类线索。
    url: str
    text: str = ""


def extract_title(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    if soup.title and soup.title.string:
        return normalize_whitespace(soup.title.string)
    h1 = soup.find("h1")
    if h1:
        return normalize_whitespace(h1.get_text(" ", strip=True))
    return ""


def extract_text_content(html: str, max_len: int = 4000) -> str:
    soup = BeautifulSoup(html or "", "html.parser")

    # script/style/noscript 对正文检索没有帮助，先剔掉能减少很多噪声。
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    text = normalize_whitespace(text)
    return truncate_text(text, max_len)


def extract_meta_description(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for attrs in (
        {"name": "description"},
        {"property": "og:description"},
        {"name": "twitter:description"},
    ):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return normalize_whitespace(str(tag.get("content")))
    return ""


def extract_link_items(html: str, base_url: str) -> List[ExtractedLink]:
    soup = BeautifulSoup(html or "", "html.parser")
    links: List[ExtractedLink] = []

    # 这里只保留 http/https 链接，像锚点、javascript 链接都不值得往后传。
    for tag in soup.find_all("a", href=True):
        href = (tag.get("href") or "").strip()
        if not href:
            continue
        if href.startswith("#"):
            continue
        if href.startswith("javascript:"):
            continue

        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        if parsed.scheme not in {"http", "https"}:
            continue

        fragmentless = parsed._replace(fragment="").geturl()
        anchor_text = normalize_whitespace(tag.get_text(" ", strip=True))
        links.append(ExtractedLink(url=fragmentless, text=anchor_text))

    # 去重保序，避免同一个页面里重复导航链接把结果列表刷满。
    seen = set()
    result: List[ExtractedLink] = []
    for item in links:
        key = normalize_url_key(item.url)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def extract_links(html: str, base_url: str) -> List[str]:
    return [item.url for item in extract_link_items(html, base_url)]
