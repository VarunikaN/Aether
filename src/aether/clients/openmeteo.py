from __future__ import annotations

import httpx

from aether.cache import FileCache
from aether.clients.http import get_json
from aether.models import Place, Weather

WMO = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "rime fog",
    51: "light drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    80: "rain showers",
    95: "thunderstorm",
}


def _wmo_text(code: int | None) -> str:
    if code is None:
        return "unknown"
    return WMO.get(code, f"code {code}")


async def fetch_weather(
    client: httpx.AsyncClient,
    place: Place,
    cache: FileCache | None = None,
) -> Weather:
    data = await get_json(
        client,
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place.lat,
            "longitude": place.lon,
            "current": "temperature_2m,precipitation,weather_code,wind_speed_10m,is_day",
            "hourly": "precipitation",
            "forecast_hours": 6,
            "timezone": "auto",
        },
        cache=cache,
        cache_key=f"openmeteo:v2:{round(place.lat, 3)}:{round(place.lon, 3)}",
    )
    current = data.get("current") or {}
    hourly = data.get("hourly") or {}
    precip_hours = [float(value) for value in (hourly.get("precipitation") or []) if value is not None]
    code = current.get("weather_code")
    return Weather(
        temp_c=None if current.get("temperature_2m") is None else float(current["temperature_2m"]),
        wind_kmh=None if current.get("wind_speed_10m") is None else float(current["wind_speed_10m"]),
        precip_mm=None if current.get("precipitation") is None else float(current["precipitation"]),
        weather_code=None if code is None else int(code),
        weather_text=_wmo_text(None if code is None else int(code)),
        next_6h_precip_mm=round(sum(precip_hours[:6]), 2) if precip_hours else 0.0,
        timezone=str(data.get("timezone") or "UTC"),
        is_day=None if current.get("is_day") is None else bool(int(current["is_day"])),
    )
