from __future__ import annotations

from datetime import datetime, timezone

import httpx

from aether.cache import FileCache
from aether.clients.http import ApiError, get_json
from aether.fusion import haversine_km
from aether.models import ISS, Place

ISS_PRIMARY = "https://api.wheretheiss.at/v1/satellites/25544"
ISS_FALLBACK = "http://api.open-notify.org/iss-now.json"


async def fetch_iss(
    client: httpx.AsyncClient,
    place: Place | None = None,
    cache: FileCache | None = None,
) -> ISS:
    try:
        data = await get_json(client, ISS_PRIMARY, cache=cache, cache_key="iss:wheretheiss")
        lat = float(data["latitude"])
        lon = float(data["longitude"])
        altitude = None if data.get("altitude") is None else float(data["altitude"])
        timestamp = datetime.fromtimestamp(int(data.get("timestamp") or 0), tz=timezone.utc)
    except (ApiError, KeyError, TypeError, ValueError):
        data = await get_json(client, ISS_FALLBACK, cache=cache, cache_key="iss:opennotify")
        position = data.get("iss_position") or {}
        lat = float(position["latitude"])
        lon = float(position["longitude"])
        altitude = None
        timestamp = datetime.fromtimestamp(int(data.get("timestamp") or 0), tz=timezone.utc)

    distance = None
    if place is not None:
        distance = round(haversine_km(place.lat, place.lon, lat, lon), 1)
    return ISS(lat=lat, lon=lon, altitude_km=altitude, timestamp=timestamp, distance_km=distance)
