from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import get_settings

"""
这个文件封装了项目里统一的 HTTP 请求方式。
这样 provider 层就不用各自处理 User-Agent、超时、错误信息拼装这些细节。
"""


def build_headers(extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    settings = get_settings()
    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def _raise_for_status(response: httpx.Response, url: str) -> None:
    # 这里把 GitHub 常见的限流头一并带进异常信息，排查起来会直接很多。
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        retry_after = response.headers.get("Retry-After")
        rate_remaining = response.headers.get("X-RateLimit-Remaining")
        rate_reset = response.headers.get("X-RateLimit-Reset")
        details = [f"HTTP {response.status_code} for {url}"]
        if retry_after:
            details.append(f"retry_after={retry_after}")
        if rate_remaining is not None:
            details.append(f"rate_limit_remaining={rate_remaining}")
        if rate_reset:
            details.append(f"rate_limit_reset={rate_reset}")
        raise RuntimeError("; ".join(details)) from exc


async def fetch_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> Any:
    settings = get_settings()
    async with httpx.AsyncClient(
        timeout=timeout or settings.request_timeout_seconds,
        follow_redirects=True,
        headers=build_headers(headers),
        trust_env=False,
    ) as client:
        response = await client.get(url, params=params)
        _raise_for_status(response, url)
        try:
            return response.json()
        except ValueError as exc:
            # 调 JSON 接口却拿到 HTML 等内容时，直接抛出更明确的错误。
            content_type = response.headers.get("content-type", "")
            raise RuntimeError(f"Expected JSON from {url}, got content-type={content_type!r}") from exc


async def fetch_text(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> str:
    settings = get_settings()
    async with httpx.AsyncClient(
        timeout=timeout or settings.request_timeout_seconds,
        follow_redirects=True,
        headers=build_headers(headers),
        trust_env=False,
    ) as client:
        response = await client.get(url, params=params)
        _raise_for_status(response, url)
        return response.text
