import json

import pytest

from aether import cli
from aether.clients import PlaceNotFound
from aether.clients.http import ApiError
from tests.test_snapshot import make_brief


def raising(exc):
    def _raise(**kwargs):
        raise exc

    return _raise


def test_scan_unknown_place_prints_clean_error(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_brief_sync", raising(PlaceNotFound("hahaha")))
    assert cli.main(["scan", "hahaha"]) == 1
    err = capsys.readouterr().err
    assert "No place found for 'hahaha'" in err
    assert "Traceback" not in err


def test_scan_network_failure_blames_the_service(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_brief_sync", raising(ApiError("nominatim: timed out")))
    assert cli.main(["scan", "Paris"]) == 1
    assert "not the place" in capsys.readouterr().err


def test_scan_bad_radius_message(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_brief_sync", raising(ValueError("Radius must be between 0 and 5000 km")))
    assert cli.main(["scan", "Paris", "--radius-km", "-1"]) == 1
    assert "Radius must be" in capsys.readouterr().err


def test_scan_lat_without_lon_is_a_usage_error():
    with pytest.raises(SystemExit) as caught:
        cli.main(["scan", "--lat", "17"])
    assert caught.value.code == 2


def test_scan_json_output(monkeypatch, capsys):
    monkeypatch.setattr(cli, "build_brief_sync", lambda **kwargs: make_brief())
    assert cli.main(["--json", "scan", "Hyderabad"]) == 0
    assert json.loads(capsys.readouterr().out)["place"]["name"] == "Hyderabad"


def test_snapshot_with_one_bad_place_writes_nothing(monkeypatch, tmp_path, capsys):
    def fake(**kwargs):
        if kwargs["query"] == "hahaha":
            raise PlaceNotFound("hahaha")
        return make_brief(name=kwargs["query"])

    monkeypatch.setattr(cli, "build_brief_sync", fake)
    out = tmp_path / "docs"
    assert cli.main(["snapshot", "--places", "Hyderabad,hahaha", "--out", str(out)]) == 1
    assert not out.exists()
    assert "left untouched" in capsys.readouterr().err


def test_snapshot_all_good_writes_files(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "build_brief_sync", lambda **kwargs: make_brief(name=kwargs["query"]))
    out = tmp_path / "docs"
    assert cli.main(["snapshot", "--places", "Hyderabad,Tokyo", "--out", str(out)]) == 0
    assert (out / "index.html").exists()


def test_snapshot_empty_places_is_a_usage_error():
    with pytest.raises(SystemExit):
        cli.main(["snapshot", "--places", " , "])
