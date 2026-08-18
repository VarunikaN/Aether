from __future__ import annotations

import httpx

from aether.cache import FileCache
from aether.clients.http import get_json
from aether.models import Disaster

EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"


async def fetch_disasters(client: httpx.AsyncClient, cache: FileCache | None = None) -> list[Disaster]:
    data = await get_json(
        client,
        EONET_URL,
        params={"limit": 20, "status": "open"},
        cache=cache,
        cache_key="eonet:open",
    )
    disasters: list[Disaster] = []
    for row in data.get("events") or []:
        categories = [str(item.get("title")) for item in (row.get("categories") or []) if item.get("title")]
        geometry = row.get("geometry") or []
        point = geometry[-1] if geometry else {}
        coords = point.get("coordinates") or [None, None]
        lon = lat = None
        if isinstance(coords, list) and len(coords) >= 2 and coords[0] is not None and coords[1] is not None:
            lon = float(coords[0])
            lat = float(coords[1])
        disasters.append(
            Disaster(
                title=str(row.get("title") or row.get("id") or "event"),
                status="open" if not row.get("closed") else "closed",
                countries=categories,
                url=str(row.get("link") or ""),
                date=str(point.get("date") or ""),
                lat=lat,
                lon=lon,
            )
        )
    return disasters
