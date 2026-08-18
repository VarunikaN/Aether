from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from aether.cache import FileCache
from aether.clients import fetch_disasters, fetch_flights, fetch_iss, fetch_quakes, fetch_weather, geocode
from aether.clients.http import ApiError
from aether.fusion import attach_quake_distances, filter_quakes, mark_disasters, score_risk, utcnow
from aether.models import Brief, Place, SourceStatus


def default_cache() -> FileCache:
    return FileCache(Path(".aether-cache"), ttl_seconds=300)


async def _settle(coro, name: str, sources: list[SourceStatus], fallback):
    try:
        value = await coro
        sources.append(SourceStatus(name=name, ok=True, detail="ok"))
        return value
    except (ApiError, ValueError, httpx.HTTPError, KeyError, TypeError) as exc:
        sources.append(SourceStatus(name=name, ok=False, detail=str(exc)))
        return fallback


async def build_brief(
    *,
    query: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 600.0,
    cache: FileCache | None = None,
) -> Brief:
    cache = cache or default_cache()
    sources: list[SourceStatus] = []
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        if query:
            place = await geocode(client, query, cache=cache)
            sources.append(SourceStatus(name="nominatim", ok=True, detail=place.display_name))
        elif lat is not None and lon is not None:
            place = Place(name=f"{lat:.3f},{lon:.3f}", lat=lat, lon=lon, display_name=f"{lat:.4f},{lon:.4f}")
            sources.append(SourceStatus(name="nominatim", ok=True, detail="coordinates supplied"))
        else:
            raise ValueError("Provide a place name or --lat and --lon")

        weather, quakes, iss, disasters = await asyncio.gather(
            _settle(fetch_weather(client, place, cache=cache), "open-meteo", sources, None),
            _settle(fetch_quakes(client, cache=cache), "usgs", sources, []),
            _settle(fetch_iss(client, place, cache=cache), "iss", sources, None),
            _settle(fetch_disasters(client, cache=cache), "eonet", sources, []),
        )
        flights = await _settle(
            fetch_flights(client, place, radius_km, cache=cache),
            "opensky",
            sources,
            [],
        )

    quakes = attach_quake_distances(quakes or [], place)
    nearby = filter_quakes(quakes, radius_km)
    disasters = mark_disasters(disasters or [], place)
    risk = score_risk(place, radius_km, nearby, weather, disasters)
    return Brief(
        generated_at=utcnow(),
        place=place,
        radius_km=radius_km,
        weather=weather,
        quakes=nearby[:12],
        flights=(flights or [])[:40],
        iss=iss,
        disasters=disasters[:8],
        risk=risk,
        sources=sources,
    )


def build_brief_sync(**kwargs) -> Brief:
    return asyncio.run(build_brief(**kwargs))
