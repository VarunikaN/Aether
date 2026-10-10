from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from aether.cache import FileCache
from aether.clients import fetch_disasters, fetch_flights, fetch_iss, fetch_quakes, fetch_weather, geocode
from aether.clients.http import ApiError
from aether.fusion import attach_quake_distances, filter_quakes, mark_disasters, score_risk, utcnow
from aether.models import Brief, Place, SourceStatus

MAX_RADIUS_KM = 5000.0
MAX_QUERY_LENGTH = 80


def default_cache() -> FileCache:
    return FileCache(Path(".aether-cache"), ttl_seconds=300)


def validate_inputs(
    query: str | None, lat: float | None, lon: float | None, radius_km: float
) -> None:
    if not (0 < radius_km <= MAX_RADIUS_KM):
        raise ValueError(f"Radius must be between 0 and {MAX_RADIUS_KM:.0f} km")
    if query:
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Place name is too long (max {MAX_QUERY_LENGTH} characters)")
        return
    if lat is None or lon is None:
        raise ValueError("Provide a place name or both --lat and --lon")
    if not (-90 <= lat <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise ValueError("Longitude must be between -180 and 180")


RISK_INPUTS = ("usgs", "open-meteo", "eonet")


def _note_data_gaps(risk, sources: list[SourceStatus]) -> None:
    missing = [item.name for item in sources if item.name in RISK_INPUTS and not item.ok]
    if missing:
        risk.reasons.insert(-1, f"Data gap: {', '.join(missing)} did not answer, so this level may be understated")


async def _settle(coro, name: str, sources: list[SourceStatus], fallback):
    try:
        value = await coro
        sources.append(SourceStatus(name=name, ok=True, detail="ok"))
        return value
    except (ApiError, ValueError, httpx.HTTPError, KeyError, TypeError) as exc:
        sources.append(SourceStatus(name=name, ok=False, detail=str(exc)))
        return fallback
    except Exception as exc:
        sources.append(SourceStatus(name=name, ok=False, detail=f"unexpected {type(exc).__name__}"))
        return fallback


async def build_brief(
    *,
    query: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 600.0,
    cache: FileCache | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> Brief:
    query = " ".join(query.split()) if query else None
    validate_inputs(query, lat, lon, radius_km)
    cache = cache or default_cache()
    sources: list[SourceStatus] = []
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, transport=transport) as client:
        if query:
            place = await geocode(client, query, cache=cache)
            sources.append(SourceStatus(name="nominatim", ok=True, detail=place.display_name))
        else:
            place = Place(name=f"{lat:.3f},{lon:.3f}", lat=lat, lon=lon, display_name=f"{lat:.4f},{lon:.4f}")
            sources.append(SourceStatus(name="nominatim", ok=True, detail="coordinates supplied"))

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
    _note_data_gaps(risk, sources)
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
