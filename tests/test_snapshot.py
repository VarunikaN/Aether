import json
from datetime import datetime, timezone
from pathlib import Path

from aether.models import Brief, Place, Risk, SourceStatus
from aether.snapshot import write_snapshot


def test_write_snapshot(tmp_path: Path):
    brief = Brief(
        generated_at=datetime(2026, 8, 18, 5, 0, tzinfo=timezone.utc),
        place=Place(name="Hyderabad", lat=17.4, lon=78.5, display_name="Hyderabad, India"),
        radius_km=600,
        weather=None,
        quakes=[],
        flights=[],
        iss=None,
        disasters=[],
        risk=Risk(level="LOW", reasons=["quiet"]),
        sources=[SourceStatus(name="usgs", ok=True, detail="ok")],
    )
    write_snapshot([brief], tmp_path)
    payload = json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8"))
    assert payload[0]["place"]["name"] == "Hyderabad"
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "AETHER SNAPSHOT" in html
    assert "Hyderabad" in html
