from __future__ import annotations

from aether.models import Brief


def _down(brief: Brief, name: str) -> bool:
    return any(item.name == name and not item.ok for item in brief.sources)


def _rate_limited(brief: Brief, name: str) -> bool:
    return any(item.name == name and not item.ok and "429" in item.detail for item in brief.sources)


def degraded_line(brief: Brief) -> str | None:
    names = [item.name for item in brief.sources if not item.ok]
    if not names:
        return None
    return f"Degraded feeds: {', '.join(names)}. Those parts are missing, not empty."


def summary_lines(brief: Brief) -> list[str]:
    weather = brief.weather
    sky_line = "I could not read the sky."
    if weather:
        temp = "—" if weather.temp_c is None else f"{weather.temp_c:.0f}°C"
        rain = weather.next_6h_precip_mm if weather.next_6h_precip_mm is not None else 0
        when = "night" if weather.is_day is False else "day"
        sky_line = (
            f"{brief.place.name} is {when}, {weather.weather_text}, {temp}. "
            f"{rain:.1f} mm of rain in the next six hours."
        )
    if _down(brief, "usgs"):
        quakes = "Quake feed unavailable."
    elif brief.quakes:
        quakes = f"{len(brief.quakes)} quake(s) inside {brief.radius_km:.0f} km."
    else:
        quakes = f"No M2.5+ quakes inside {brief.radius_km:.0f} km."
    flights = "Aircraft feed unavailable." if _down(brief, "opensky") else f"{len(brief.flights)} aircraft in the box."
    iss = "ISS position unknown."
    if brief.iss and brief.iss.distance_km is not None:
        iss = f"ISS is {brief.iss.distance_km:.0f} km from you."
    lines = [
        sky_line,
        f"Risk {brief.risk.level}. {quakes} {flights} {iss}",
    ]
    note = degraded_line(brief)
    if note:
        lines.append(note)
    lines.append("Say weather, flights, quakes, ISS, events — or a different city.")
    return lines


def weather_lines(brief: Brief) -> list[str]:
    weather = brief.weather
    if weather is None:
        return ["The weather feed did not answer.", "Try flights, quakes, or a city name."]
    wind = "—" if weather.wind_kmh is None else f"{weather.wind_kmh:.0f} km/h"
    now = "—" if weather.precip_mm is None else f"{weather.precip_mm:.1f} mm"
    later = "—" if weather.next_6h_precip_mm is None else f"{weather.next_6h_precip_mm:.1f} mm"
    return [
        f"{weather.weather_text}. Wind {wind}. Rain now {now}, next six hours {later}.",
        "Flights, quakes, ISS, or a city name?",
    ]


def quake_lines(brief: Brief) -> list[str]:
    if _down(brief, "usgs"):
        return [
            "The earthquake feed did not answer, so I can't say whether the ground is quiet.",
            "Weather, flights, or a city name?",
        ]
    if not brief.quakes:
        return [
            f"Quiet ground. Nothing M2.5+ within {brief.radius_km:.0f} km in the last day.",
            "Weather, flights, or a city name?",
        ]
    lines = ["Closest shakes:"]
    for quake in brief.quakes[:5]:
        km = "—" if quake.distance_km is None else f"{quake.distance_km:.0f} km"
        lines.append(f"M{quake.mag:.1f}   {km}   {quake.place}")
    lines.append("Risk, weather, or a city name?")
    return lines


def flight_lines(brief: Brief) -> list[str]:
    if _rate_limited(brief, "opensky"):
        return ["OpenSky rate-limited this request (HTTP 429), so there is no flight data.", "Weather, ISS, or a city name?"]
    if _down(brief, "opensky"):
        return ["OpenSky did not answer, so there is no flight data.", "Weather, ISS, or a city name?"]
    if not brief.flights:
        return ["OpenSky answered, but no aircraft are airborne in the box.", "Weather, ISS, or a city name?"]
    lines = [f"{len(brief.flights)} airborne. Sample:"]
    for flight in brief.flights[:8]:
        alt = "—" if flight.altitude_m is None else f"{flight.altitude_m:.0f} m"
        speed = "—" if flight.velocity_ms is None else f"{flight.velocity_ms * 3.6:.0f} km/h"
        lines.append(f"{flight.callsign:<8}  {flight.origin_country:<14}  {alt:>8}  {speed}")
    lines.append("Say weather, ISS, events — or another city.")
    return lines


def iss_lines(brief: Brief | None) -> list[str]:
    if brief is None or brief.iss is None:
        return ["I lost the station.", "Name a city first."]
    iss = brief.iss
    alt = "—" if iss.altitude_km is None else f"{iss.altitude_km:.0f} km"
    dist = "—" if iss.distance_km is None else f"{iss.distance_km:.0f} km from {brief.place.name}"
    return [
        f"ISS at {iss.lat:.2f}, {iss.lon:.2f}. Altitude {alt}. {dist}.",
        iss.timestamp.strftime("%Y-%m-%d %H:%M UTC"),
        "Weather, flights, or a city name?",
    ]


def event_lines(brief: Brief) -> list[str]:
    if _down(brief, "eonet"):
        return ["NASA's event feed did not answer, so I can't say whether anything is open nearby.", "Risk, weather, or a city name?"]
    near = [item for item in brief.disasters if item.in_country]
    pool = near[:5] if near else brief.disasters[:3]
    if not pool:
        return ["EONET is quiet.", "Weather or a city name?"]
    header = "Nearby natural events:" if near else "Nothing nearby. Farther open events:"
    lines = [header]
    for item in pool:
        km = "—" if item.distance_km is None else f"{item.distance_km:.0f} km"
        lines.append(f"{item.title}   {km}")
    lines.append("Risk, weather, or a city name?")
    return lines


def risk_lines(brief: Brief) -> list[str]:
    lines = [f"Risk {brief.risk.level}."]
    lines.extend(brief.risk.reasons)
    lines.append("Weather, flights, quakes, or a city name?")
    return lines


def answer(intent: str, brief: Brief | None) -> list[str]:
    if brief is None:
        return ["Name a city first."]
    if intent == "weather":
        return weather_lines(brief)
    if intent == "quakes":
        return quake_lines(brief)
    if intent == "flights":
        return flight_lines(brief)
    if intent == "iss":
        return iss_lines(brief)
    if intent == "events":
        return event_lines(brief)
    if intent == "risk":
        return risk_lines(brief)
    if intent == "all":
        return summary_lines(brief)
    if intent == "stay":
        return [
            f"Still over {brief.place.name}.",
            "Weather, flights, quakes, ISS, events — or a different city.",
        ]
    if intent == "help":
        return ["Weather, flights, quakes, ISS, events, risk, a city name, or quit."]
    return ["I only follow cities and sky topics. Try weather, flights, ISS, or Hyderabad."]
