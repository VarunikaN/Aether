from __future__ import annotations

import math
from datetime import datetime, timezone

from aether.models import Disaster, Place, Quake, Risk, Weather


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def bbox_from_radius(lat: float, lon: float, radius_km: float) -> tuple[float, float, float, float]:
    lat_delta = radius_km / 111.0
    cos_lat = math.cos(math.radians(lat))
    lon_delta = radius_km / (111.0 * max(0.2, abs(cos_lat)))
    lamin = max(-90.0, lat - lat_delta)
    lamax = min(90.0, lat + lat_delta)
    lomin = max(-180.0, lon - lon_delta)
    lomax = min(180.0, lon + lon_delta)
    return lamin, lomin, lamax, lomax


def attach_quake_distances(quakes: list[Quake], place: Place) -> list[Quake]:
    nearby: list[Quake] = []
    for quake in quakes:
        quake.distance_km = round(haversine_km(place.lat, place.lon, quake.lat, quake.lon), 1)
        nearby.append(quake)
    nearby.sort(key=lambda item: (item.distance_km or 1e9, -item.mag))
    return nearby


def filter_quakes(quakes: list[Quake], radius_km: float) -> list[Quake]:
    return [item for item in quakes if item.distance_km is not None and item.distance_km <= radius_km]


def mark_disasters(disasters: list[Disaster], place: Place, nearby_km: float = 1500.0) -> list[Disaster]:
    country = (place.country or "").lower()
    code = (place.country_code or "").lower()
    for item in disasters:
        names = [name.lower() for name in item.countries]
        country_hit = False
        if country:
            country_hit = country in names or any(country in name or name in country for name in names)
        if code:
            country_hit = country_hit or any(code in name for name in names)
        if item.lat is not None and item.lon is not None:
            item.distance_km = round(haversine_km(place.lat, place.lon, item.lat, item.lon), 1)
            nearby = item.distance_km <= nearby_km
        else:
            nearby = False
        item.in_country = country_hit or nearby
    disasters.sort(key=lambda item: (not item.in_country, item.distance_km or 1e9))
    return disasters


def score_risk(
    place: Place,
    radius_km: float,
    quakes: list[Quake],
    weather: Weather | None,
    disasters: list[Disaster],
) -> Risk:
    reasons: list[str] = []
    level = "LOW"

    close_major = [q for q in quakes if q.distance_km is not None and q.distance_km <= min(300, radius_km) and q.mag >= 5.5]
    close_strong = [q for q in quakes if q.distance_km is not None and q.distance_km <= min(500, radius_km) and q.mag >= 4.5]
    close_moderate = [q for q in quakes if q.distance_km is not None and q.distance_km <= radius_km and q.mag >= 3.5]
    rain = weather.next_6h_precip_mm if weather and weather.next_6h_precip_mm is not None else 0.0
    local_disasters = [item for item in disasters if item.in_country]

    if close_major:
        level = "HIGH"
        top = close_major[0]
        reasons.append(f"M{top.mag:.1f} quake {top.distance_km:.0f} km away ({top.place})")
    if rain >= 40 and local_disasters:
        level = "HIGH"
        reasons.append(f"{rain:.0f} mm rain in next 6h with a nearby natural event")
    if level != "HIGH" and (close_strong or rain >= 20):
        level = "ELEVATED"
        if close_strong:
            top = close_strong[0]
            reasons.append(f"M{top.mag:.1f} quake {top.distance_km:.0f} km away ({top.place})")
        if rain >= 20:
            reasons.append(f"{rain:.0f} mm precipitation forecast in next 6h")
    if level in {"LOW"} and (close_moderate or local_disasters):
        level = "MODERATE"
        if close_moderate:
            top = close_moderate[0]
            reasons.append(f"M{top.mag:.1f} quake {top.distance_km:.0f} km away ({top.place})")
        if local_disasters:
            reasons.append(f"Nearby event: {local_disasters[0].title}")

    if not reasons:
        reasons.append(
            f"No significant quakes near {place.name} within {radius_km:.0f} km and no heavy rain in the next 6h"
        )
    reasons.append("Situational brief from public feeds — not an official warning")
    return Risk(level=level, reasons=reasons)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
