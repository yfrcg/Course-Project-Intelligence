from __future__ import annotations

from urllib.parse import urlparse


GITHUB_HOSTS = {"github.com", "www.github.com"}


def looks_like_url(value: str) -> bool:
    normalized = (value or "").strip()
    return "://" in normalized or normalized.startswith("github.com/")


def normalize_github_repo_input(value: str) -> str | None:
    normalized = (value or "").strip()
    if not normalized:
        return None

    if not looks_like_url(normalized):
        parts = [part.strip() for part in normalized.split("/") if part.strip()]
        if len(parts) == 2:
            owner, repo = parts
            repo = repo.removesuffix(".git")
            return f"{owner}/{repo}" if owner and repo else None
        return None

    candidate = normalized if "://" in normalized else f"https://{normalized}"
    parsed = urlparse(candidate)
    if parsed.netloc.lower() not in GITHUB_HOSTS:
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None

    owner = parts[0].strip()
    repo = parts[1].strip().removesuffix(".git")
    if not owner or not repo:
        return None
    return f"{owner}/{repo}"


def is_github_repo_url(url: str) -> bool:
    normalized = (url or "").strip()
    if not normalized or not looks_like_url(normalized):
        return False
    return normalize_github_repo_input(normalized) is not None


def canonical_github_repo_url(value: str) -> str | None:
    repo = normalize_github_repo_input(value)
    if repo is None:
        return None
    return f"https://github.com/{repo}"
