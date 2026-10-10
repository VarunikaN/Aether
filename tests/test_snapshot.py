import json
from datetime import datetime, timezone
from pathlib import Path

from aether.models import Brief, Place, Risk, SourceStatus
from aether.snapshot import write_snapshot


def make_brief(name="Hyderabad", reasons=None, sources=None):
    return Brief(
        generated_at=datetime(2026, 8, 18, 5, 0, tzinfo=timezone.utc),
        place=Place(name=name, lat=17.4, lon=78.5, display_name=f"{name}, India"),
        radius_km=600,
        weather=None,
        quakes=[],
        flights=[],
        iss=None,
        disasters=[],
        risk=Risk(level="LOW", reasons=reasons or ["quiet"]),
        sources=sources or [SourceStatus(name="usgs", ok=True, detail="ok")],
    )


def test_write_snapshot(tmp_path: Path):
    write_snapshot([make_brief()], tmp_path)
    payload = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert payload[0]["place"]["name"] == "Hyderabad"
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "AETHER SNAPSHOT" in html
    assert "Hyderabad" in html


def test_snapshot_escapes_feed_text(tmp_path: Path):
    write_snapshot([make_brief(name="<script>alert(1)</script>", reasons=["<img src=x onerror=1>"])], tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    assert "<img src=x" not in html


def test_snapshot_shows_unavailable_not_zero_when_feeds_down(tmp_path: Path):
    sources = [
        SourceStatus(name="usgs", ok=False, detail="down"),
        SourceStatus(name="opensky", ok=False, detail="HTTP 429"),
    ]
    write_snapshot([make_brief(sources=sources)], tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Quake feed unavailable" in html
    assert "Degraded feeds: usgs, opensky" in html
