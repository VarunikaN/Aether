from __future__ import annotations

import argparse
import json
from pathlib import Path

from aether.collect import build_brief_sync
from aether.snapshot import write_snapshot
from aether.tui import run as run_app
from aether.voice import summary_lines


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aether",
        description="Weather-coded terminal assistant for live Earth-risk briefs.",
    )
    parser.add_argument("--json", action="store_true", help="With scan: print JSON instead of text")
    sub = parser.add_subparsers(dest="command")

    scan = sub.add_parser("scan", help="One-shot brief for a place (no TUI)")
    scan.add_argument("place", nargs="?", help="City or place name")
    scan.add_argument("--lat", type=float)
    scan.add_argument("--lon", type=float)
    scan.add_argument("--radius-km", type=float, default=600.0)

    snap = sub.add_parser("snapshot", help="Write static HTML/JSON for GitHub Pages")
    snap.add_argument("--places", default="Hyderabad,Tokyo")
    snap.add_argument("--out", default="docs")
    snap.add_argument("--radius-km", type=float, default=600.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command is None:
        return run_app()

    if args.command == "scan":
        if not args.place and (args.lat is None or args.lon is None):
            return run_app()
        brief = build_brief_sync(
            query=args.place,
            lat=args.lat,
            lon=args.lon,
            radius_km=args.radius_km,
        )
        if args.json:
            print(json.dumps(brief.to_dict(), indent=2))
        else:
            print("\n".join(summary_lines(brief)))
        return 0

    if args.command == "snapshot":
        places = [item.strip() for item in args.places.split(",") if item.strip()]
        briefs = [build_brief_sync(query=place, radius_km=args.radius_km) for place in places]
        out = Path(args.out)
        write_snapshot(briefs, out)
        print(f"Wrote {out / 'index.html'}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
