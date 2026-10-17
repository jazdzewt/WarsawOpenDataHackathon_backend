import threading
import time

import requests

from app.core.config import settings


class UmApiError(RuntimeError):
    pass


class UmApiClient:
    """Klient API dane.um.warszawa.pl z prostym cache (dane zmieniają się co kilka minut)."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[dict]]] = {}
        self._lock = threading.Lock()

    def fetch(self, action: str) -> list[dict]:
        with self._lock:
            cached = self._cache.get(action)
            if cached and time.monotonic() - cached[0] < settings.um_api_cache_seconds:
                return cached[1]

        try:
            response = requests.post(
                f"{settings.um_api_base_url}/{action}",
                headers={"Authorization": settings.api_key},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise UmApiError(f"{action}: {exc}") from exc

        # Odpowiedź to lista rekordów; na wszelki wypadek obsługujemy też {"result": [...]}
        if isinstance(payload, dict):
            payload = payload.get("result", payload.get("data", []))
        if not isinstance(payload, list):
            raise UmApiError(f"{action}: nieoczekiwany format odpowiedzi")

        with self._lock:
            self._cache[action] = (time.monotonic(), payload)
        return payload

    def pogoda(self) -> list[dict]:
        return self.fetch(settings.um_action_pogoda)

    def powietrze(self) -> list[dict]:
        return self.fetch(settings.um_action_powietrze)

    def boiska(self) -> list[dict]:
        return self.fetch(settings.um_action_boiska)

    def zajecia(self) -> list[dict]:
        return self.fetch(settings.um_action_zajecia)


um_api = UmApiClient()
