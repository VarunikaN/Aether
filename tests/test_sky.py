from aether.models import Weather
from aether.sky import sky_from_weather


def test_rain_codes_to_rain_sky():
    weather = Weather(28, 10, 1, 61, "slight rain", 4.0, is_day=True)
    assert sky_from_weather(weather).name == "rain"


def test_clear_night():
    weather = Weather(18, 5, 0, 0, "clear", 0.0, is_day=False)
    assert sky_from_weather(weather).name == "clear_night"
