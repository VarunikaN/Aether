import asyncio

import httpx
import pytest

from aether.cache import FileCache
from aether.clients import PlaceNotFound
from aether.collect import build_brief, validate_inputs
from aether.voice import flight_lines, quake_lines, summary_lines

NOMINATIM = [
    {
        "name": "Hyderabad",
        "addresstype": "city",
        "category": "boundary",
        "importance": 0.6,
        "lat": "17.38",
        "lon": "78.48",
        "display_name": "Hyderabad, Telangana, India",
        "address": {"country": "India", "country_code": "in"},
        "namedetails": {"name": "Hyderabad"},
    }
]
WEATHER = {
    "current": {"temperature_2m": 30, "precipitation": 0, "weather_code": 1, "wind_speed_10m": 8, "is_day": 1},
    "hourly": {"precipitation": [0, 0, 0, 0, 0, 0]},
    "timezone": "Asia/Kolkata",
}
USGS = {"features": [{"geometry": {"coordinates": [78.6, 17.5, 10]}, "properties": {"mag": 5.8, "place": "near X", "time": 0}}]}
ISS = {"latitude": 10.0, "longitude": 20.0, "altitude": 420.0, "timestamp": 1}
EONET = {"events": []}
OPENSKY = {"states": [["abc123", "AI101 ", "India", 0, 0, 78.4, 17.4, 9000.0, False, 220.0]]}


def transport(overrides=None):
    overrides = overrides or {}

    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host in overrides:
            return overrides[host](request)
        table = {
            "nominatim.openstreetmap.org": NOMINATIM,
            "api.open-meteo.com": WEATHER,
            "earthquake.usgs.gov": USGS,
            "api.wheretheiss.at": ISS,
            "eonet.gsfc.nasa.gov": EONET,
            "opensky-network.org": OPENSKY,
        }
        return httpx.Response(200, json=table[host])

    return httpx.MockTransport(handler)


def brief(tmp_path, **kwargs):
    cache = FileCache(tmp_path, 300)
    return asyncio.run(build_brief(query="hyderabad", cache=cache, transport=transport(kwargs.get("overrides")), radius_km=kwargs.get("radius", 600.0)))


def test_happy_path_builds_full_brief(tmp_path):
    result = brief(tmp_path)
    assert result.risk.level == "HIGH"
    assert all(item.ok for item in result.sources)
    assert len(result.flights) == 1


def test_opensky_429_degrades_but_brief_survives(tmp_path):
    result = brief(tmp_path, overrides={"opensky-network.org": lambda r: httpx.Response(429, text="slow")})
    status = {item.name: item for item in result.sources}
    assert status["opensky"].ok is False
    assert "429" in status["opensky"].detail
    assert result.flights == []
    assert "rate-limited" in flight_lines(result)[0]
    assert any("Degraded feeds: opensky" in line for line in summary_lines(result))
    assert "Aircraft feed unavailable." in " ".join(summary_lines(result))


def test_quake_feed_down_is_not_reported_as_quiet(tmp_path):
    result = brief(tmp_path, overrides={"earthquake.usgs.gov": lambda r: httpx.Response(500, text="x")})
    assert "Quake feed unavailable." in " ".join(summary_lines(result))
    assert "can't say" in quake_lines(result)[0]
    assert any(reason.startswith("Data gap: usgs") for reason in result.risk.reasons)
    assert result.risk.reasons[-1].startswith("Situational brief")


def test_malformed_feed_does_not_crash_the_brief(tmp_path):
    result = brief(tmp_path, overrides={"opensky-network.org": lambda r: httpx.Response(200, json=["not", "a", "dict"])})
    assert {item.name: item.ok for item in result.sources}["opensky"] is False


def test_iss_falls_back_to_open_notify(tmp_path):
    fallback = {"iss_position": {"latitude": "5.0", "longitude": "6.0"}, "timestamp": 1}
    result = brief(
        tmp_path,
        overrides={
            "api.wheretheiss.at": lambda r: httpx.Response(500, text="x"),
            "api.open-notify.org": lambda r: httpx.Response(200, json=fallback),
        },
    )
    assert result.iss is not None and result.iss.lat == 5.0


def test_unknown_place_raises_not_found(tmp_path):
    with pytest.raises(PlaceNotFound):
        asyncio.run(
            build_brief(
                query="hahaha",
                cache=FileCache(tmp_path, 300),
                transport=transport({"nominatim.openstreetmap.org": lambda r: httpx.Response(200, json=[])}),
            )
        )


@pytest.mark.parametrize(
    "query,lat,lon,radius",
    [
        (None, None, None, 600.0),
        (None, 91.0, 0.0, 600.0),
        (None, 0.0, 181.0, 600.0),
        (None, 10.0, None, 600.0),
        ("Paris", None, None, 0.0),
        ("Paris", None, None, -5.0),
        ("Paris", None, None, 99999.0),
        ("x" * 200, None, None, 600.0),
    ],
)
def test_invalid_inputs_are_rejected(query, lat, lon, radius):
    with pytest.raises(ValueError):
        validate_inputs(query, lat, lon, radius)


def test_valid_coordinates_pass():
    validate_inputs(None, 17.38, 78.48, 600.0)
