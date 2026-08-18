from __future__ import annotations

from dataclasses import dataclass

from aether.models import Brief, Weather


@dataclass(frozen=True)
class Sky:
    name: str
    mood: str


TWILIGHT = Sky(name="twilight", mood="waiting on a place")

SKIES = {
    "clear_day": Sky("clear_day", "hard sun"),
    "clear_night": Sky("clear_night", "clear night"),
    "cloud": Sky("cloud", "under cloud"),
    "rain": Sky("rain", "wet air"),
    "storm": Sky("storm", "charged"),
    "fog": Sky("fog", "low vis"),
    "snow": Sky("snow", "cold quiet"),
}


def sky_from_weather(weather: Weather | None, risk_level: str = "LOW") -> Sky:
    if weather is None:
        base = TWILIGHT
    else:
        code = weather.weather_code if weather.weather_code is not None else 1
        night = weather.is_day is False
        if code >= 95:
            base = SKIES["storm"]
        elif code in {71, 73, 75, 77, 85, 86}:
            base = SKIES["snow"]
        elif code in {45, 48}:
            base = SKIES["fog"]
        elif code >= 51:
            base = SKIES["rain"]
        elif code >= 2:
            base = SKIES["cloud"]
        elif night:
            base = SKIES["clear_night"]
        else:
            base = SKIES["clear_day"]
    if risk_level == "HIGH":
        return Sky(base.name, f"{base.mood} · high risk")
    if risk_level == "ELEVATED":
        return Sky(base.name, f"{base.mood} · elevated")
    return base


def sky_from_brief(brief: Brief) -> Sky:
    return sky_from_weather(brief.weather, brief.risk.level)
