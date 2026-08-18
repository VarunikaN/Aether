from __future__ import annotations

import httpx

from aether.cache import FileCache
from aether.clients.http import get_json
from aether.fusion import bbox_from_radius
from aether.models import Flight, Place

OPENSKY_URL = "https://opensky-network.org/api/states/all"


async def fetch_flights(
    client: httpx.AsyncClient,
    place: Place,
    radius_km: float,
    cache: FileCache | None = None,
) -> list[Flight]:
    lamin, lomin, lamax, lomax = bbox_from_radius(place.lat, place.lon, radius_km)
    data = await get_json(
        client,
        OPENSKY_URL,
        params={"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax},
        cache=cache,
        cache_key=f"opensky:{round(place.lat, 2)}:{round(place.lon, 2)}:{int(radius_km)}",
    )
    flights: list[Flight] = []
    for row in data.get("states") or []:
        if not row or len(row) < 10:
            continue
        lon, lat = row[5], row[6]
        if lon is None or lat is None:
            continue
        on_ground = bool(row[8])
        if on_ground:
            continue
        flights.append(
            Flight(
                icao24=str(row[0] or ""),
                callsign=str(row[1] or "").strip() or "unknown",
                origin_country=str(row[2] or ""),
                lon=float(lon),
                lat=float(lat),
                altitude_m=None if row[7] is None else float(row[7]),
                velocity_ms=None if row[9] is None else float(row[9]),
            )
        )
    return flights
