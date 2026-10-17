import pytest
import requests

from app.services import geocoding
from app.services.geocoding import GeoPoint, geocode_address


class FakeResponse:
    """Minimalna atrapa odpowiedzi HTTP: zwraca JSON i ewentualnie rzuca błąd statusu."""

    def __init__(self, payload, status_error: Exception | None = None) -> None:
        self._payload = payload
        self._status_error = status_error

    def json(self):
        return self._payload

    def raise_for_status(self) -> None:
        if self._status_error:
            raise self._status_error


@pytest.fixture(autouse=True)
def no_rate_limit_sleep(monkeypatch):
    # Nominatim ma limit 1 zapytania na sekundę. W testach wyłączamy czekanie,
    # a cache funkcji czyścimy, żeby testy nie wpływały na siebie.
    monkeypatch.setattr(geocoding.time, "sleep", lambda _: None)
    geocode_address.cache_clear()
    yield
    geocode_address.cache_clear()


def fake_get(monkeypatch, response: FakeResponse, calls: list | None = None):
    def _get(url, params=None, headers=None, timeout=None):
        if calls is not None:
            calls.append({"url": url, "params": params, "headers": headers})
        return response

    monkeypatch.setattr(geocoding.requests, "get", _get)


def test_returns_coordinates_and_district(monkeypatch) -> None:
    fake_get(
        monkeypatch,
        FakeResponse(
            [
                {
                    "lat": "52.2297",
                    "lon": "21.0122",
                    "display_name": "Marszałkowska 10, Warszawa",
                    "address": {"city_district": "Śródmieście"},
                }
            ]
        ),
    )
    point = geocode_address("Marszałkowska 10")
    assert point == GeoPoint(52.2297, 21.0122, "Śródmieście", "Marszałkowska 10, Warszawa")


def test_district_falls_back_to_suburb(monkeypatch) -> None:
    fake_get(
        monkeypatch,
        FakeResponse([{"lat": "52.18", "lon": "21.00", "address": {"suburb": "Mokotów"}}]),
    )
    assert geocode_address("Domaniewska 39").district == "Mokotów"


def test_returns_none_when_address_not_found(monkeypatch) -> None:
    fake_get(monkeypatch, FakeResponse([]))
    assert geocode_address("Nieistniejąca 999") is None


def test_sends_warsaw_restricted_query_and_user_agent(monkeypatch) -> None:
    calls: list = []
    fake_get(monkeypatch, FakeResponse([]), calls)
    geocode_address("Marszałkowska 10")

    params = calls[0]["params"]
    # Wyszukiwanie ma być ograniczone do Polski i prostokąta Warszawy.
    assert params["q"] == "Marszałkowska 10, Warszawa"
    assert params["countrycodes"] == "pl"
    assert params["viewbox"] == geocoding.WARSAW_VIEWBOX
    assert params["bounded"] == 1
    assert calls[0]["headers"]["User-Agent"] == geocoding.USER_AGENT


def test_http_error_is_propagated(monkeypatch) -> None:
    error = requests.HTTPError("503 Service Unavailable")
    fake_get(monkeypatch, FakeResponse([], status_error=error))
    with pytest.raises(requests.HTTPError):
        geocode_address("Marszałkowska 10")


def test_results_are_cached(monkeypatch) -> None:
    calls: list = []
    fake_get(monkeypatch, FakeResponse([]), calls)
    geocode_address("Marszałkowska 10")
    geocode_address("Marszałkowska 10")
    # Drugie wywołanie z tym samym adresem nie może wysłać kolejnego zapytania.
    assert len(calls) == 1
