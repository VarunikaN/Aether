from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


@dataclass
class Place:
    name: str
    lat: float
    lon: float
    country: str = ""
    country_code: str = ""
    display_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Quake:
    mag: float
    place: str
    lat: float
    lon: float
    depth_km: float
    time_utc: datetime
    url: str
    distance_km: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["time_utc"] = _iso(self.time_utc)
        return data


@dataclass
class Flight:
    icao24: str
    callsign: str
    origin_country: str
    lat: float
    lon: float
    altitude_m: float | None
    velocity_ms: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Weather:
    temp_c: float | None
    wind_kmh: float | None
    precip_mm: float | None
    weather_code: int | None
    weather_text: str
    next_6h_precip_mm: float | None
    timezone: str = "UTC"
    is_day: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ISS:
    lat: float
    lon: float
    altitude_km: float | None
    timestamp: datetime
    distance_km: float | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = _iso(self.timestamp)
        return data


@dataclass
class Disaster:
    title: str
    status: str
    countries: list[str]
    url: str
    date: str
    in_country: bool = False
    lat: float | None = None
    lon: float | None = None
    distance_km: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SourceStatus:
    name: str
    ok: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Risk:
    level: str
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Brief:
    generated_at: datetime
    place: Place
    radius_km: float
    weather: Weather | None
    quakes: list[Quake]
    flights: list[Flight]
    iss: ISS | None
    disasters: list[Disaster]
    risk: Risk
    sources: list[SourceStatus]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": _iso(self.generated_at),
            "place": self.place.to_dict(),
            "radius_km": self.radius_km,
            "weather": None if self.weather is None else self.weather.to_dict(),
            "quakes": [item.to_dict() for item in self.quakes],
            "flights": [item.to_dict() for item in self.flights],
            "iss": None if self.iss is None else self.iss.to_dict(),
            "disasters": [item.to_dict() for item in self.disasters],
            "risk": self.risk.to_dict(),
            "sources": [item.to_dict() for item in self.sources],
        }
