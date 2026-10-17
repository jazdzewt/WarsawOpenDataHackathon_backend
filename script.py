import os

import requests
from dotenv import load_dotenv

load_dotenv(".env.example")

BASE_URL = "https://dane.um.warszawa.pl/api/action"


def call_api(action, api_key=None, params=None, data=None, timeout=30):
    """Wysyła POST do https://dane.um.warszawa.pl/api/action/<action>
    z kluczem API w nagłówku Authorization."""
    api_key = api_key or os.environ["API_KEY"]
    response = requests.post(
        f"{BASE_URL}/{action}",
        headers={"Authorization": api_key},
        params=params,
        json=data,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Prostokąt obejmujący Warszawę: lon_min, lat_max, lon_max, lat_min
WARSAW_VIEWBOX = "20.85,52.37,21.28,52.09"


def geocode_address(address, timeout=10):
    """Zamienia adres w Warszawie na (latitude, longitude) przez Nominatim (OSM).
    Zwraca None, jeśli adresu nie znaleziono."""
    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": f"{address}, Warszawa",
            "format": "json",
            "limit": 1,
            "countrycodes": "pl",
            "viewbox": WARSAW_VIEWBOX,
            "bounded": 1,
        },
        headers={"User-Agent": "WarsawOpenDataHackathon/1.0"},
        timeout=timeout,
    )
    response.raise_for_status()
    results = response.json()
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


if __name__ == "__main__":
    print(geocode_address("Marszałkowska 1"))
    print(call_api("get_zom_pogoda"))
