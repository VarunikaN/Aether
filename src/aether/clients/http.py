from __future__ import annotations

from typing import Any

import httpx

from aether import USER_AGENT
from aether.cache import FileCache


class ApiError(RuntimeError):
    pass


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
    except httpx.HTTPError as exc:
        if cache and cache_key:
            stale = cache.get_stale(cache_key)
            if stale is not None:
                return stale
        raise ApiError(f"{url}: {exc}") from exc
    if cache and cache_key:
        cache.set(cache_key, data)
    return data
