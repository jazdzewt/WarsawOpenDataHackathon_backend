import pytest
import requests

from app.core.config import settings
from app.services import um_api as um_api_module
from app.services.um_api import UmApiClient, UmApiError


class FakeResponse:
    """Atrapa odpowiedzi HTTP dla requests.post."""

    def __init__(self, payload=None, json_error: Exception | None = None) -> None:
        self._payload = payload
        self._json_error = json_error

    def raise_for_status(self) -> None:
        pass

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


@pytest.fixture
def client() -> UmApiClient:
    # Osobny klient dla każdego testu, żeby cache nie przenosił się między testami.
    return UmApiClient()


def fake_post(monkeypatch, response: FakeResponse | Exception, calls: list | None = None):
    def _post(url, headers=None, timeout=None):
        if calls is not None:
            calls.append({"url": url, "headers": headers})
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(um_api_module.requests, "post", _post)


def test_returns_list_payload(monkeypatch, client) -> None:
    records = [{"nazwa": "Boisko A"}, {"nazwa": "Boisko B"}]
    fake_post(monkeypatch, FakeResponse(records))
    assert client.fetch("akcja") == records


def test_unwraps_result_key(monkeypatch, client) -> None:
    # Odpowiedź może mieć postać {"result": [...]} - wtedy zwracamy samą listę.
    fake_post(monkeypatch, FakeResponse({"result": [{"a": 1}]}))
    assert client.fetch("akcja") == [{"a": 1}]


def test_unexpected_format_raises(monkeypatch, client) -> None:
    fake_post(monkeypatch, FakeResponse({"error": "coś innego"}))
    with pytest.raises(UmApiError, match="nieoczekiwany format"):
        client.fetch("akcja")


def test_network_error_is_wrapped(monkeypatch, client) -> None:
    fake_post(monkeypatch, requests.ConnectionError("brak sieci"))
    with pytest.raises(UmApiError, match="brak sieci"):
        client.fetch("akcja")


def test_invalid_json_is_wrapped(monkeypatch, client) -> None:
    fake_post(monkeypatch, FakeResponse(json_error=ValueError("nie JSON")))
    with pytest.raises(UmApiError):
        client.fetch("akcja")


def test_sends_api_key_in_authorization_header(monkeypatch, client) -> None:
    monkeypatch.setattr(settings, "api_key", "sekretny-klucz")
    calls: list = []
    fake_post(monkeypatch, FakeResponse([]), calls)
    client.fetch("akcja")
    assert calls[0]["headers"]["Authorization"] == "sekretny-klucz"
    assert calls[0]["url"].endswith("/akcja")


def test_second_call_is_served_from_cache(monkeypatch, client) -> None:
    calls: list = []
    fake_post(monkeypatch, FakeResponse([{"x": 1}]), calls)
    client.fetch("akcja")
    client.fetch("akcja")
    # Dane są świeże (w granicach um_api_cache_seconds), więc drugi raz nie idziemy do API.
    assert len(calls) == 1


def test_cache_expires(monkeypatch, client) -> None:
    calls: list = []
    fake_post(monkeypatch, FakeResponse([{"x": 1}]), calls)
    monkeypatch.setattr(settings, "um_api_cache_seconds", 0)
    client.fetch("akcja")
    client.fetch("akcja")
    # Przy czasie cache równym 0 każde wywołanie musi pobrać dane ponownie.
    assert len(calls) == 2
