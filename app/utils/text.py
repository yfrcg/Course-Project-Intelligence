from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List
from urllib.parse import parse_qsl, urlsplit

"""
这个文件收纳项目里反复会用到的文本小工具。
它们本身很轻，但 query 分析、归一化、排序解释都会依赖这里的行为保持一致。
"""


# 这些词对检索贡献太弱，做关键词抽取时直接过滤掉。
STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "by",
    "course", "project", "lab", "homework", "assignment", "github", "gitee",
    "公开", "项目", "课程", "实验", "大作业", "仓库", "资料", "相关", "一个", "一些",
}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def safe_lower(text: str) -> str:
    return normalize_whitespace(text).lower()


def truncate_text(text: str, max_len: int = 240) -> str:
    text = normalize_whitespace(text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def tokenize(text: str) -> List[str]:
    text = safe_lower(text)
    # 保留中英文、数字以及仓库名里常见的 `_`, `-`, `.`，避免把 repo 名切得太碎。
    parts = re.split(r"[^a-zA-Z0-9\u4e00-\u9fff\-_+.#]+", text)
    return [p for p in parts if p]


def extract_keywords(text: str, top_k: int = 8) -> List[str]:
    tokens = tokenize(text)
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) >= 2]
    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(top_k)]


def guess_year(text: str) -> int | None:
    matches = re.findall(r"\b(20\d{2})\b", text or "")
    if not matches:
        return None
    years = [int(x) for x in matches]
    years.sort(reverse=True)
    return years[0]


def normalize_url_key(url: str) -> str:
    if not url:
        return ""

    # 去重时不关心协议和 query 参数顺序，所以这里做一个稳定化 key。
    parsed = urlsplit(url.strip())
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    if query_items:
        query = "&".join(f"{key}={value}" for key, value in sorted(query_items))
        return f"{host}{path}?{query}"
    return f"{host}{path}"


def unique_preserve_order(items: Iterable[str]) -> List[str]:
    # 这个辅助函数在 query 拼接和标签合并里很常用，目标是“去重但不打乱先后顺序”。
    seen = set()
    result: List[str] = []
    for item in items:
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
