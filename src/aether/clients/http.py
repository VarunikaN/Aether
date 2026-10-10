from __future__ import annotations

from typing import Any

import httpx

from aether import USER_AGENT
from aether.cache import FileCache


class ApiError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status

    @property
    def rate_limited(self) -> bool:
        return self.status == 429


def _describe(url: str, exc: Exception) -> tuple[str, int | None]:
    host = httpx.URL(url).host
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 429:
            return f"{host}: rate limited (HTTP 429)", status
        return f"{host}: HTTP {status}", status
    if isinstance(exc, httpx.TimeoutException):
        return f"{host}: timed out", None
    if isinstance(exc, httpx.HTTPError):
        return f"{host}: connection failed", None
    return f"{host}: unreadable response", None


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    cache: FileCache | None = None,
    cache_key: str | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    if cache and cache_key:
        hit = cache.get(cache_key)
        if hit is not None:
            return hit
    merged = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        merged.update(headers)
    try:
        response = await client.get(url, params=params, headers=merged)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        if cache and cache_key:
            stale = cache.get_stale(cache_key)
            if stale is not None:
                return stale
        message, status = _describe(url, exc)
        raise ApiError(message, status=status) from exc
    if cache and cache_key:
        cache.set(cache_key, data)
    return data
