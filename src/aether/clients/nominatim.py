from __future__ import annotations

import asyncio
import difflib
import re
import time
import unicodedata
from typing import Any

import httpx

from aether.cache import FileCache
from aether.clients.http import get_json
from aether.models import Place

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MIN_INTERVAL_SECONDS = 1.0
NAME_MATCH_THRESHOLD = 0.85
SUGGEST_THRESHOLD = 0.70

PLACE_KINDS = {
    "city",
    "town",
    "village",
    "hamlet",
    "suburb",
    "municipality",
    "city_district",
    "borough",
    "district",
    "county",
    "state_district",
    "state",
    "province",
    "region",
    "island",
    "country",
}

_last_request = 0.0


class PlaceNotFound(ValueError):
    def __init__(self, query: str, suggestion: str | None = None) -> None:
        super().__init__(f"No place found for {query!r}")
        self.query = query
        self.suggestion = suggestion


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^\w]+", " ", stripped.casefold()).strip()


def _names(hit: dict[str, Any]) -> list[str]:
    names = {str(hit.get("name") or "")}
    names.update(str(value) for value in (hit.get("namedetails") or {}).values())
    address = hit.get("address") or {}
    for key in ("city", "town", "village", "hamlet", "state", "country"):
        if address.get(key):
            names.add(str(address[key]))
    return [name for name in names if name]


def name_similarity(query: str, hit: dict[str, Any]) -> float:
    wanted = _fold(query)
    if not wanted:
        return 0.0
    wanted_words = set(wanted.split())
    best = 0.0
    for name in _names(hit):
        folded = _fold(name)
        if not folded:
            continue
        if folded == wanted:
            return 1.0
        if wanted_words and wanted_words <= set(folded.split()):
            best = max(best, 0.9)
        best = max(best, difflib.SequenceMatcher(None, wanted, folded).ratio())
    return best


def is_place_kind(hit: dict[str, Any]) -> bool:
    return str(hit.get("addresstype") or "") in PLACE_KINDS


def pick_place(query: str, hits: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    suggestion: tuple[float, str] | None = None
    for hit in hits:
        if not is_place_kind(hit):
            continue
        score = name_similarity(query, hit)
        if score >= NAME_MATCH_THRESHOLD:
            return hit, None
        if score >= SUGGEST_THRESHOLD and (suggestion is None or score > suggestion[0]):
            suggestion = (score, str(hit.get("name") or ""))
    return None, suggestion[1] if suggestion else None


async def _throttle() -> None:
    global _last_request
    wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request = time.monotonic()


def _place_from(hit: dict[str, Any], query: str) -> Place:
    address = hit.get("address") or {}
    name = (
        hit.get("name")
        or address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("state")
        or query
    )
    return Place(
        name=str(name),
        lat=float(hit["lat"]),
        lon=float(hit["lon"]),
        country=str(address.get("country") or ""),
        country_code=str(address.get("country_code") or "").upper(),
        display_name=str(hit.get("display_name") or query),
    )


async def geocode(client: httpx.AsyncClient, query: str, cache: FileCache | None = None) -> Place:
    query = " ".join(query.split())
    if not query:
        raise PlaceNotFound(query)
    key = f"nominatim:v2:{query.lower()}"
    cached = cache.get(key) if cache else None
    if cached is None:
        await _throttle()
    hits = await get_json(
        client,
        NOMINATIM_URL,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 10,
            "addressdetails": 1,
            "namedetails": 1,
            "accept-language": "en",
        },
        cache=cache,
        cache_key=key,
    )
    if not isinstance(hits, list):
        raise PlaceNotFound(query)
    hit, suggestion = pick_place(query, hits)
    if hit is None:
        raise PlaceNotFound(query, suggestion)
    return _place_from(hit, query)
