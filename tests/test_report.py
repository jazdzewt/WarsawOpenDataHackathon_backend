import json
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import geocoding
from app.services.geocoding import GeoPoint
from app.services.um_api import UmApiError, um_api

client = TestClient(app)
SAMPLES = Path(__file__).resolve().parents[1]  # przykładowe odpowiedzi API

POINTS = {
    "Marszałkowska 10": GeoPoint(52.2297, 21.0122, "Śródmieście", "Marszałkowska 10, Śródmieście, Warszawa"),
    "Domaniewska 39": GeoPoint(52.1805, 21.0050, "Mokotów", "Domaniewska 39, Mokotów, Warszawa"),
}
ACTIONS = {
    settings.um_action_pogoda: "pogoda",
    settings.um_action_powietrze: "powietrze",
    settings.um_action_boiska: "boiska",
    settings.um_action_zajecia: "zajecia",
}


@pytest.fixture(autouse=True)
def fake_sources(monkeypatch):
    def fake_fetch(action):
        return json.loads((SAMPLES / f"{ACTIONS[action]}.json").read_text(encoding="utf-8"))

    monkeypatch.setattr(um_api, "fetch", fake_fetch)
    monkeypatch.setattr(geocoding, "geocode_address", lambda address: POINTS.get(address))


def post(**overrides):
    body = {"home_address": "Marszałkowska 10", "work_address": "Domaniewska 39", "date": "2026-10-19"}
    return client.post("/api/v1/report", json=body | overrides)


def test_report_combines_all_sources() -> None:
    response = post()
    assert response.status_code == 200
    report = response.json()
    assert report["errors"] == []
    assert report["date"] == "2026-10-19"
    for key, district in (("home", "Śródmieście"), ("work", "Mokotów")):
        loc = report[key]
        assert loc["district"] == district
        assert loc["weather"]["station"].startswith("Stacja")
        assert loc["air_quality"]["index"]
        assert loc["outdoor"]["suitable"] in (True, False)
        assert loc["pitches"], key
        assert all(p["district"] == district and p["hours"] != "-" for p in loc["pitches"])
        assert all(a["distance_km"] is None or a["distance_km"] <= 2.0 for a in loc["activities"])


def test_activities_filtered_by_weekday() -> None:
    # 2026-10-19 to poniedziałek
    for loc in (post().json()["home"], post().json()["work"]):
        for activity in loc["activities"]:
            assert not activity["days"] or "Poniedziałek" in activity["days"]


def test_unknown_address_returns_422() -> None:
    response = post(home_address="Nieistniejąca 999")
    assert response.status_code == 422
    assert "dom" in response.json()["detail"]


def test_failed_source_is_reported_not_fatal(monkeypatch) -> None:
    original = um_api.fetch

    def failing_fetch(action):
        if action == settings.um_action_powietrze:
            raise UmApiError("timeout")
        return original(action)

    monkeypatch.setattr(um_api, "fetch", failing_fetch)
    report = post().json()
    assert len(report["errors"]) == 1 and "powietrze" in report["errors"][0]
    assert report["home"]["air_quality"] is None
    assert report["home"]["weather"] is not None


def test_bad_weather_marks_outdoor_unsuitable(monkeypatch) -> None:
    original = um_api.fetch

    def rainy(action):
        records = original(action)
        if action == settings.um_action_pogoda:
            records = [r | {"int_opadu": 2.5} for r in records]
        return records

    monkeypatch.setattr(um_api, "fetch", rainy)
    outdoor = post().json()["home"]["outdoor"]
    assert outdoor["suitable"] is False
    assert any("Opady" in r for r in outdoor["reasons"])
