from __future__ import annotations


def format_citation_hint(title: str, url: str | None) -> str:
    normalized_title = (title or "").strip() or "Untitled source"
    normalized_url = (url or "").strip()
    if normalized_url:
        return f"Learning reference only: {normalized_title} - {normalized_url}"
    return f"Learning reference only: {normalized_title} - source unavailable"
