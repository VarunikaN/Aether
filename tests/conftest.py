import pytest

from aether.clients import nominatim


@pytest.fixture(autouse=True)
def no_throttle(monkeypatch):
    monkeypatch.setattr(nominatim, "MIN_INTERVAL_SECONDS", 0.0)
