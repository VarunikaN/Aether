# Aether

Terminal assistant that fuses live public feeds into a weather-coded Earth-risk brief for one place.

It asks where to look. You answer with a city (or `weather`, `flights`, `quakes`, `ISS`, `events`). The HUD recodes to that sky — rain, storm, clear night, fog — and the assistant replies from USGS, OpenSky, Open-Meteo, ISS, and NASA EONET.

This is a situational brief, not an official warning product.

```text
python -m aether
you: Hyderabad
```

## Pipeline

```text
utterance
    → intent (city vs topic vs stay/move; refuse non-places)
    → Nominatim (cached)
    → bbox from radius
    → parallel: USGS · Open-Meteo · ISS · EONET
    → OpenSky bbox (degrades on 429)
    → haversine filter + rule-based risk
    → Textual HUD  |  JSON  |  static HTML snapshot
```

Failed sources are marked degraded. The brief still renders.

## Data sources

| API | Role | Auth |
| --- | --- | --- |
| [Nominatim](https://nominatim.org/release-docs/latest/api/Overview/) | Geocode | None (User-Agent required) |
| [USGS earthquakes](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) | M≥2.5, last 24 hours | None |
| [OpenSky Network](https://opensky-network.org/apidoc/index.html) | Airborne traffic in bbox | None (rate-limited) |
| [Open-Meteo](https://open-meteo.com/) | Current weather, `is_day`, 6-hour rain | None |
| [Where The ISS At](https://wheretheiss.at/w/developer) / [Open Notify](http://open-notify.org/Open-Notify-API/) | ISS position | None |
| [NASA EONET](https://eonet.gsfc.nasa.gov/docs/v3) | Open natural events | None |

## Risk rules

Transparent heuristics, not a trained model.

| Level | When |
| --- | --- |
| **HIGH** | M≥5.5 within 300 km, or >40 mm rain in the next 6 hours plus a nearby EONET event |
| **ELEVATED** | M≥4.5 within 500 km, or >20 mm rain in the next 6 hours |
| **MODERATE** | M≥3.5 in radius, or an EONET event within ~1500 km |
| **LOW** | Otherwise |

## Setup

Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m aether
```

Docker (needs a TTY):

```bash
docker compose run --rm aether
```

## Commands

| Command | What it does |
| --- | --- |
| `python -m aether` | Interactive HUD. `Ctrl+Q` quits. |
| `python -m aether scan Hyderabad` | One-shot text brief |
| `python -m aether --json scan Hyderabad` | Same, JSON on stdout |
| `python -m aether scan --lat 17.385 --lon 78.486 --radius-km 600` | Brief by coordinates |
| `python -m aether snapshot --out docs` | Static HTML/JSON for GitHub Pages |

In the HUD, phrases such as `stay here` stay on the current city. They are not geocoded.

## Tests

```bash
pytest
```

Network is not required. Live lookups need outbound HTTPS.

A GitHub Action refreshes `docs/` every six hours so Pages can serve a timestamped snapshot that does not depend on a sleeping PaaS dyno.

## Limitations

- OpenSky anonymous access is often rate-limited; flight counts may be empty.
- Nominatim allows at most one request per second; place lookups are cached for five minutes.
- Risk is a documented rule set. It is not a forecast, insurance, or emergency product.
- ReliefWeb v2 requires a pre-approved app name, so natural events come from EONET.

## Layout

```text
src/aether/tui.py           Textual HUD
src/aether/talk.py          Intent parsing
src/aether/voice.py         Assistant replies
src/aether/collect.py       Fan-out and fusion
src/aether/clients/         One module per public API
src/aether/fusion.py        Distance, bbox, risk
src/aether/atmosphere.py    Rain / star / sun field
docs/                       Optional Pages snapshot
```
