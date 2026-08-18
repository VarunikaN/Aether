from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class FileCache:
    def __init__(self, root: Path, ttl_seconds: int = 300) -> None:
        self.root = root
        self.ttl_seconds = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in key)
        return self.root / f"{safe}.json"

    def get(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        stored_at = payload.get("stored_at", 0)
        if time.time() - stored_at > self.ttl_seconds:
            return None
        return payload.get("data")

    def get_stale(self, key: str) -> Any | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload.get("data")

    def set(self, key: str, data: Any) -> None:
        path = self._path(key)
        path.write_text(
            json.dumps({"stored_at": time.time(), "data": data}, default=str),
            encoding="utf-8",
        )
