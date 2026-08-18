from __future__ import annotations

from datetime import datetime, timezone

import httpx

from aether.cache import FileCache
from aether.clients.http import get_json
from aether.models import Quake

USGS_FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"


async def fetch_quakes(client: httpx.AsyncClient, cache: FileCache | None = None) -> list[Quake]:
    data = await get_json(client, USGS_FEED, cache=cache, cache_key="usgs:2.5_day")
    quakes: list[Quake] = []
    for feature in data.get("features") or []:
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or [None, None, None]
        props = feature.get("properties") or {}
        mag = props.get("mag")
        if mag is None or coords[0] is None or coords[1] is None:
            continue
        time_ms = props.get("time") or 0
        quakes.append(
            Quake(
                mag=float(mag),
                place=str(props.get("place") or "unknown"),
                lon=float(coords[0]),
                lat=float(coords[1]),
                depth_km=float(coords[2] or 0.0),
                time_utc=datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc),
                url=str(props.get("url") or ""),
            )
        )
    return quakes
