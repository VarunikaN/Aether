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

Failed sources are marked degraded. The brief still renders, and a feed that is down is reported as unavailable, never as "quiet" or "0 aircraft".

## AI domain

Aether uses **no machine learning and no LLM**. It is a rule-based data-fusion and decision-support system, in the tradition of expert systems: it gathers live feeds, normalises them, and applies explicit thresholds to produce a risk level that can be explained line by line.

| Domain | Used here? |
| --- | --- |
| Generative AI (LLMs, text or image generation) | No. Assistant replies are fixed templates |
| Agentic AI (autonomous multi-step agents, tool use) | No. It runs a fixed pipeline and never decides what to do next |
| Machine learning (trained or learned models) | No. Thresholds are hand-set heuristics |
| Rule-based data fusion / decision support | Yes |

The chat-style interface is a rules-and-regex intent parser, not a language model. Natural extensions, none of which are built: a learned risk model trained on historical events, an LLM that writes the brief, and an agent that monitors a place and alerts you.

## Error handling

- **Unknown places are refused.** Nominatim also indexes shops, rivers and postcodes, so a result is accepted only if it is a real place type (city, town, village, state, country and so on) and its name resembles what you typed. Checked live: `Bangalor` resolves to Bengaluru, `Tokio` to Tokyo and `Londn` to London, while `hahaha`, `asdf`, `xyzzyplugh` and `Hydrabad` (which Nominatim only matches to a shop and a restaurant) reply "No place found". Obvious chatter, emoji, symbols and bare numbers never reach the geocoder. When a real place name is close but not close enough, the reply offers it as a suggestion instead of guessing.
- **Confirmation.** The HUD says "Locked on {resolved name}" so a wrong match is visible.
- **Service down vs not found.** A geocoder outage ("couldn't reach the place lookup") is reported differently from "that place doesn't exist".
- **Rate limits.** Nominatim calls are spaced one second apart. An OpenSky 429 is reported as rate limited, not as an empty sky.
- **Input validation.** Radius must be 1 to 5000 km, coordinates are range-checked, `--lat` needs `--lon`, queries are capped at 80 characters, and the HUD caps typed input at 200.
- **Snapshots** escape all feed text and are all-or-nothing: a partial run never overwrites a good snapshot.

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

94 tests, no network required: HTTP is exercised through `httpx.MockTransport`, and the HUD through Textual's `run_test`. Live lookups need outbound HTTPS.

A GitHub Action refreshes `docs/` every six hours so Pages can serve a timestamped snapshot that does not depend on a sleeping PaaS dyno.

## Limitations

- OpenSky anonymous access is often rate-limited; the brief then says flights are rate limited instead of reporting zero aircraft.
- OpenStreetMap is the source of truth for what exists. A name that is a real place on the map resolves even if it sounds fictional (`the moon` locks onto a place in Alabama), which is why the HUD prints the full resolved name.
- Nominatim allows at most one request per second; place lookups are cached for five minutes.
- Risk is a documented rule set. It is not a forecast, insurance, or emergency product.
- ReliefWeb v2 requires a pre-approved app name, so natural events come from EONET.

## Layout

```text
src/aether/tui.py           Textual HUD
src/aether/talk.py          Intent parsing
src/aether/voice.py         Assistant replies
src/aether/collect.py       Fan-out and fusion
src/aether/clients/         One module per public API (HTTP layer, Nominatim, feeds)
src/aether/fusion.py        Distance, bbox, risk
src/aether/snapshot.py      Static HTML / JSON snapshot
src/aether/atmosphere.py    Rain / star / sun field
tests/                      Unit and integration tests (mocked HTTP)
docs/                       Optional Pages snapshot
```
