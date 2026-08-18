from __future__ import annotations

import json
from pathlib import Path

from aether.models import Brief

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Aether snapshot</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; background: #07111c; color: #e8eef5; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
    h1 {{ letter-spacing: 0.18em; font-size: 0.85rem; color: #7dd3fc; }}
    h2 {{ font-size: 1.4rem; margin: 0.2rem 0 1rem; }}
    .meta {{ color: #93a4b8; font-size: 0.9rem; }}
    .risk {{ display: inline-block; padding: 0.2rem 0.6rem; border: 1px solid #334155; border-radius: 999px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin: 1.25rem 0; }}
    .card {{ background: #0d1b2a; border: 1px solid #1e3a5f; border-radius: 12px; padding: 0.9rem 1rem; }}
    .label {{ color: #7dd3fc; font-size: 0.72rem; letter-spacing: 0.08em; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.9rem; }}
    th, td {{ text-align: left; padding: 0.45rem 0.3rem; border-bottom: 1px solid #1e3a5f; }}
    ul {{ line-height: 1.5; }}
    .note {{ margin-top: 2rem; color: #93a4b8; font-size: 0.85rem; }}
  </style>
</head>
<body>
<main>
  <h1>AETHER SNAPSHOT</h1>
  {body}
  <p class="note">Static snapshot from public APIs. Run <code>python -m aether</code> for the live terminal assistant. Not an official warning product.</p>
</main>
</body>
</html>
"""


def _brief_html(brief: Brief) -> str:
    weather = brief.weather
    weather_line = "unavailable"
    if weather:
        weather_line = (
            f"{weather.temp_c}°C {weather.weather_text}, next 6h rain {weather.next_6h_precip_mm} mm"
        )
    iss_line = "unavailable"
    if brief.iss:
        iss_line = f"{brief.iss.lat:.2f}, {brief.iss.lon:.2f}"
        if brief.iss.distance_km is not None:
            iss_line += f" ({brief.iss.distance_km:.0f} km)"
    quake_rows = "".join(
        f"<tr><td>{q.mag:.1f}</td><td>{q.distance_km:.0f}</td><td>{q.place}</td></tr>"
        for q in brief.quakes[:8]
        if q.distance_km is not None
    ) or "<tr><td colspan='3'>None in radius</td></tr>"
    reasons = "".join(f"<li>{item}</li>" for item in brief.risk.reasons)
    return f"""
  <h2>{brief.place.name}</h2>
  <p class="meta">{brief.place.display_name}<br/>{brief.generated_at.strftime('%Y-%m-%d %H:%M UTC')} · radius {brief.radius_km:.0f} km</p>
  <p><span class="risk">RISK {brief.risk.level}</span></p>
  <div class="grid">
    <div class="card"><div class="label">WEATHER</div><div>{weather_line}</div></div>
    <div class="card"><div class="label">QUAKES</div><div>{len(brief.quakes)}</div></div>
    <div class="card"><div class="label">FLIGHTS</div><div>{len(brief.flights)}</div></div>
    <div class="card"><div class="label">ISS</div><div>{iss_line}</div></div>
  </div>
  <ul>{reasons}</ul>
  <table><thead><tr><th>Mag</th><th>km</th><th>Place</th></tr></thead><tbody>{quake_rows}</tbody></table>
"""


def write_snapshot(briefs: list[Brief], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = [brief.to_dict() for brief in briefs]
    (out_dir / "snapshot.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    body = "\n".join(_brief_html(brief) for brief in briefs)
    (out_dir / "index.html").write_text(HTML_TEMPLATE.format(body=body), encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
