import threading
import time
from dataclasses import dataclass
from functools import lru_cache

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Prostokąt obejmujący Warszawę: lon_min, lat_max, lon_max, lat_min
WARSAW_VIEWBOX = "20.85,52.37,21.28,52.09"
USER_AGENT = "WarsawOpenDataHackathon/1.0"

_lock = threading.Lock()
_last_call = 0.0


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float
    district: str | None
    display_name: str


@lru_cache(maxsize=512)
def geocode_address(address: str, timeout: float = 10) -> GeoPoint | None:
    """Zamienia adres w Warszawie na współrzędne i dzielnicę (Nominatim / OSM).
    Zwraca None, jeśli adresu nie znaleziono."""
    global _last_call
    with _lock:
        # Nominatim pozwala na max 1 zapytanie na sekundę
        wait = 1.0 - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()

    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": f"{address}, Warszawa",
            "format": "json",
            "limit": 1,
            "countrycodes": "pl",
            "viewbox": WARSAW_VIEWBOX,
            "bounded": 1,
            "addressdetails": 1,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    result = results[0]
    details = result.get("address", {})
    return GeoPoint(
        lat=float(result["lat"]),
        lon=float(result["lon"]),
        district=details.get("city_district") or details.get("suburb"),
        display_name=result.get("display_name", address),
    )
