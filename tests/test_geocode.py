import asyncio

import httpx
import pytest

from aether.cache import FileCache
from aether.clients import PlaceNotFound, geocode
from aether.clients.http import ApiError


def hit(name, addresstype, category="boundary", importance=0.5, details=None, **address):
    return {
        "name": name,
        "category": category,
        "addresstype": addresstype,
        "importance": importance,
        "lat": "17.38",
        "lon": "78.48",
        "display_name": f"{name}, Somewhere",
        "address": {"country": "India", "country_code": "in", **address},
        "namedetails": details or {"name": name},
    }


def run(hits=None, status=200, text=None, query="x", cache=None, calls=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        if text is not None:
            return httpx.Response(status, text=text)
        return httpx.Response(status, json=hits if hits is not None else [])

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await geocode(client, query, cache=cache)

    return asyncio.run(go())


def test_real_city_resolves():
    place = run([hit("Hyderabad", "city", city="Hyderabad")], query="hyderabad")
    assert place.name == "Hyderabad"
    assert place.country_code == "IN"


def test_shop_with_same_name_is_not_a_place():
    hits = [hit("hahaha", "shop", category="shop"), hit("Hahaha", "amenity", category="amenity")]
    with pytest.raises(PlaceNotFound):
        run(hits, query="hahaha")


def test_postcode_and_river_are_not_places():
    hits = [hit("12345", "postcode", category="place"), hit("Lol", "river", category="waterway")]
    with pytest.raises(PlaceNotFound):
        run(hits, query="lol")


def test_empty_result_is_not_found():
    with pytest.raises(PlaceNotFound):
        run([], query="xyzqwerty")


def test_similar_name_is_rejected_when_too_different():
    with pytest.raises(PlaceNotFound):
        run([hit("Asdorf", "village")], query="asdf")


def test_alternate_name_resolves():
    mumbai = hit("Mumbai", "city", details={"name": "Mumbai", "old_name": "Bombay"})
    assert run([mumbai], query="bombay").name == "Mumbai"


def test_non_latin_and_accents_resolve():
    sao = hit("São Paulo", "city")
    assert run([sao], query="sao paulo").name == "São Paulo"


def test_one_letter_typo_still_resolves():
    assert run([hit("Hyderabad", "city")], query="hyderbad").name == "Hyderabad"


def test_rough_typo_suggests_instead_of_guessing():
    with pytest.raises(PlaceNotFound) as caught:
        run([hit("Hyderabad", "city")], query="hydrbd")
    assert caught.value.suggestion == "Hyderabad"


def test_first_valid_place_wins_over_earlier_junk():
    hits = [hit("Delhi", "shop", category="shop"), hit("Delhi", "city")]
    assert run(hits, query="delhi").name == "Delhi"


def test_rate_limit_is_reported_as_429():
    with pytest.raises(ApiError) as caught:
        run(status=429, text="slow down", query="paris")
    assert caught.value.rate_limited
    assert "429" in str(caught.value)


def test_server_error_is_api_error_not_not_found():
    with pytest.raises(ApiError) as caught:
        run(status=503, text="down", query="paris")
    assert caught.value.status == 503


def test_malformed_json_is_api_error():
    with pytest.raises(ApiError):
        run(status=200, text="<html>not json</html>", query="paris")


def test_non_list_payload_is_not_found():
    with pytest.raises(PlaceNotFound):
        run(hits=None, status=200, text='{"error": "bad"}', query="paris")


def test_cache_avoids_second_request(tmp_path):
    cache = FileCache(tmp_path, 300)
    calls = []
    run([hit("Tokyo", "city")], query="tokyo", cache=cache, calls=calls)
    run([hit("Tokyo", "city")], query="tokyo", cache=cache, calls=calls)
    assert len(calls) == 1


def test_not_found_is_cached_too(tmp_path):
    cache = FileCache(tmp_path, 300)
    calls = []
    for _ in range(2):
        with pytest.raises(PlaceNotFound):
            run([], query="zzzzzz", cache=cache, calls=calls)
    assert len(calls) == 1


def test_stale_cache_used_when_service_fails(tmp_path):
    cache = FileCache(tmp_path, 0)
    run([hit("Tokyo", "city")], query="tokyo", cache=cache)
    assert run(status=500, text="down", query="tokyo", cache=cache).name == "Tokyo"


def test_uncached_lookups_are_spaced_at_least_one_interval(monkeypatch, tmp_path):
    from aether.clients import nominatim

    delays = []
    real_sleep = asyncio.sleep

    async def record(seconds):
        delays.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(nominatim, "MIN_INTERVAL_SECONDS", 1.0)
    monkeypatch.setattr(nominatim, "_last_request", 0.0)
    monkeypatch.setattr(nominatim.asyncio, "sleep", record)
    cache = FileCache(tmp_path, 300)
    run([hit("Tokyo", "city")], query="tokyo", cache=cache)
    assert delays == []
    run([hit("Paris", "city")], query="paris", cache=cache)
    assert delays and 0.5 < delays[0] <= 1.0


def test_cached_lookup_does_not_wait(monkeypatch, tmp_path):
    from aether.clients import nominatim

    cache = FileCache(tmp_path, 300)
    run([hit("Tokyo", "city")], query="tokyo", cache=cache)
    delays = []

    async def record(seconds):
        delays.append(seconds)

    monkeypatch.setattr(nominatim, "MIN_INTERVAL_SECONDS", 1.0)
    monkeypatch.setattr(nominatim.asyncio, "sleep", record)
    run([hit("Tokyo", "city")], query="tokyo", cache=cache)
    assert delays == []
