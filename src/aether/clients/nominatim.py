from __future__ import annotations

import httpx

from aether.cache import FileCache
from aether.clients.http import get_json
from aether.models import Place


async def geocode(client: httpx.AsyncClient, query: str, cache: FileCache | None = None) -> Place:
    data = await get_json(
        client,
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
        cache=cache,
        cache_key=f"nominatim:{query.lower().strip()}",
    )
    if not data:
        raise ValueError(f"No geocode result for {query!r}")
    hit = data[0]
    address = hit.get("address") or {}
    country = address.get("country") or ""
    code = (address.get("country_code") or "").upper()
    name = address.get("city") or address.get("town") or address.get("state") or query
    return Place(
        name=str(name),
        lat=float(hit["lat"]),
        lon=float(hit["lon"]),
        country=str(country),
        country_code=str(code),
        display_name=str(hit.get("display_name") or query),
    )
