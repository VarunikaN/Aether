from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from aether.clients import PlaceNotFound
from aether.clients.http import ApiError
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


def _explain(exc: Exception, query: str | None = None) -> str:
    if isinstance(exc, PlaceNotFound):
        hint = f" Did you mean {exc.suggestion}?" if exc.suggestion else ""
        return f"No place found for {exc.query!r}. Check the spelling or try a larger nearby city.{hint}"
    if isinstance(exc, ApiError):
        return f"Lookup failed: {exc}. This is the service or your connection, not the place."
    if isinstance(exc, ValueError):
        return str(exc)
    return f"Unexpected error ({type(exc).__name__}). Try again."


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command is None:
        return run_app()

    if args.command == "scan":
        if (args.lat is None) != (args.lon is None):
            parser.error("scan needs both --lat and --lon, or a place name")
        if not args.place and args.lat is None:
            return run_app()
        try:
            brief = build_brief_sync(
                query=args.place,
                lat=args.lat,
                lon=args.lon,
                radius_km=args.radius_km,
            )
        except Exception as exc:
            print(f"aether: {_explain(exc)}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(brief.to_dict(), indent=2))
        else:
            print("\n".join(summary_lines(brief)))
        return 0

    if args.command == "snapshot":
        places = [item.strip() for item in args.places.split(",") if item.strip()]
        if not places:
            parser.error("snapshot needs at least one place in --places")
        briefs = []
        failures = []
        for place in places:
            try:
                briefs.append(build_brief_sync(query=place, radius_km=args.radius_km))
            except Exception as exc:
                failures.append(f"{place}: {_explain(exc)}")
        if failures:
            for line in failures:
                print(f"aether: {line}", file=sys.stderr)
            print("aether: snapshot not written; existing files were left untouched.", file=sys.stderr)
            return 1
        out = Path(args.out)
        write_snapshot(briefs, out)
        print(f"Wrote {out / 'index.html'}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
