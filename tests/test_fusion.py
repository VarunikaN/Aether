from datetime import datetime, timezone

from aether.fusion import bbox_from_radius, haversine_km, score_risk
from aether.models import Disaster, Place, Quake, Weather


def test_haversine_hyderabad_to_self_is_zero():
    assert haversine_km(17.385, 78.486, 17.385, 78.486) < 0.01


def test_bbox_contains_center():
    lamin, lomin, lamax, lomax = bbox_from_radius(17.385, 78.486, 600)
    assert lamin < 17.385 < lamax
    assert lomin < 78.486 < lomax


def test_risk_low_when_quiet():
    place = Place(name="Hyderabad", lat=17.4, lon=78.5, country="India", country_code="IN")
    weather = Weather(
        temp_c=30,
        wind_kmh=8,
        precip_mm=0,
        weather_code=0,
        weather_text="clear",
        next_6h_precip_mm=1.0,
        is_day=True,
    )
    risk = score_risk(place, 600, [], weather, [])
    assert risk.level == "LOW"


def test_risk_elevated_for_nearby_m45():
    place = Place(name="Hyderabad", lat=17.4, lon=78.5, country="India", country_code="IN")
    quake = Quake(
        mag=4.7,
        place="near Hyderabad",
        lat=17.5,
        lon=78.6,
        depth_km=10,
        time_utc=datetime.now(timezone.utc),
        url="",
        distance_km=40,
    )
    weather = Weather(30, 8, 0, 0, "clear", 0.0, is_day=True)
    risk = score_risk(place, 600, [quake], weather, [])
    assert risk.level == "ELEVATED"


def test_risk_high_for_rain_and_local_disaster():
    place = Place(name="Hyderabad", lat=17.4, lon=78.5, country="India", country_code="IN")
    weather = Weather(28, 20, 12, 63, "moderate rain", 45.0, is_day=False)
    disaster = Disaster(
        title="India: Floods",
        status="ongoing",
        countries=["India"],
        url="",
        date="2026-08-01",
        in_country=True,
    )
    risk = score_risk(place, 600, [], weather, [disaster])
    assert risk.level == "HIGH"
