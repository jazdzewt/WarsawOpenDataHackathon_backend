"""ETL: boiska z API Warszawy -> geokodowanie (Nominatim) -> SQLite (boiska.db)."""

import os
import re
import sqlite3
import sys
import time
import unicodedata

import requests
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

API_URL = "https://dane.um.warszawa.pl/api/action/get_be_otwarte_boiska"
API_KEY = os.getenv("WARSAW_API_KEY", "")
DB_PATH = "boiska.db"
TABLE = "boiska"
NOMINATIM_DELAY_S = 1.1

ADDRESS_PREFIX_RE = re.compile(
    r"^\s*(ul|al|aleja|aleje|pl|plac|os|osiedle|rondo|skwer|bulw|bulwar)\.?\s+",
    re.IGNORECASE,
)


def extract() -> list[dict]:
    if not API_KEY:
        sys.exit("Ustaw zmienną środowiskową WARSAW_API_KEY")
    response = requests.post(API_URL, headers={"Authorization": API_KEY}, timeout=30)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):
        data = data.get("result", data.get("records", []))
        if isinstance(data, dict):
            data = data.get("records", [])
    return data


def clean_address(address: str | None) -> str:
    if not address:
        return ""
    return ADDRESS_PREFIX_RE.sub("", address).strip()


def to_column_name(key: str) -> str:
    ascii_key = (
        unicodedata.normalize("NFKD", key.replace("ł", "l").replace("Ł", "L"))
        .encode("ascii", "ignore")
        .decode()
    )
    return re.sub(r"\W+", "_", ascii_key).strip("_").lower()


def geocode_records(records: list[dict]) -> None:
    geolocator = Nominatim(user_agent="warsaw-open-data-hackathon-boiska")
    cache: dict[str, tuple[float | None, float | None]] = {}

    for i, record in enumerate(records, start=1):
        street = clean_address(record.get("Adres obiektu"))
        district = record.get("Dzielnica") or ""
        query = ", ".join(p for p in (street, district, "Warszawa", "Polska") if p)

        if query not in cache:
            try:
                location = geolocator.geocode(query, timeout=10)
            except (GeocoderTimedOut, GeocoderServiceError) as exc:
                print(f"[{i}/{len(records)}] błąd geokodowania '{query}': {exc}")
                location = None
            cache[query] = (location.latitude, location.longitude) if location else (None, None)
            time.sleep(NOMINATIM_DELAY_S)

        record["lat"], record["lon"] = cache[query]
        print(f"[{i}/{len(records)}] {query} -> {cache[query]}")


def load(records: list[dict]) -> None:
    source_keys = list(dict.fromkeys(k for r in records for k in r if k not in ("lat", "lon")))
    columns = {key: to_column_name(key) for key in source_keys}

    column_defs = ", ".join(f'"{col}" TEXT' for col in columns.values())
    insert_cols = ", ".join(f'"{col}"' for col in [*columns.values(), "lat", "lon"])
    placeholders = ", ".join("?" for _ in range(len(columns) + 2))

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f'DROP TABLE IF EXISTS "{TABLE}"')
        conn.execute(
            f'CREATE TABLE "{TABLE}" ('
            f"id INTEGER PRIMARY KEY AUTOINCREMENT, {column_defs}, lat REAL, lon REAL)"
        )
        conn.executemany(
            f'INSERT INTO "{TABLE}" ({insert_cols}) VALUES ({placeholders})',
            [[r.get(k) for k in source_keys] + [r.get("lat"), r.get("lon")] for r in records],
        )


def geocode_with_retry(geolocator: Nominatim, query: str, attempts: int = 4):
    for attempt in range(attempts):
        try:
            return geolocator.geocode(query, timeout=15)
        except (GeocoderTimedOut, GeocoderServiceError) as exc:
            wait = 10 * 2**attempt
            print(f"  błąd '{query}': {exc}; ponawiam za {wait}s")
            time.sleep(wait)
    return None


def query_variants(address: str | None, district: str | None) -> list[str]:
    street = clean_address(address)
    street = re.split(r"\s+-\s+|,", street)[0].strip()
    street = re.sub(r"\b[A-ZŁŚŻŹĆŃÓ]\.\s*", "", street).strip()
    variants = [
        ", ".join(p for p in (street, district, "Warszawa", "Polska") if p),
        f"{street}, Warszawa, Polska",
    ]
    street_no_letter = re.sub(r"(\d+)\s*[a-zA-Z]?(\s*/.*)?$", r"\1", street)
    variants.append(f"{street_no_letter}, Warszawa, Polska")
    variants.append(f"{street_no_letter}, Warsaw")
    return list(dict.fromkeys(variants))


def retry_missing(delay_s: float = 2.0) -> None:
    geolocator = Nominatim(user_agent="warsaw-open-data-hackathon-boiska")
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            f'SELECT id, adres_obiektu, dzielnica FROM "{TABLE}" WHERE lat IS NULL'
        ).fetchall()
        print(f"Rekordów bez współrzędnych: {len(rows)}")

        cache: dict[tuple, tuple[float, float] | None] = {}
        for i, (row_id, address, district) in enumerate(rows, start=1):
            key = (address, district)
            if key not in cache:
                cache[key] = None
                for query in query_variants(address, district):
                    location = geocode_with_retry(geolocator, query)
                    time.sleep(delay_s)
                    if location:
                        cache[key] = (location.latitude, location.longitude)
                        break
            if cache[key]:
                conn.execute(
                    f'UPDATE "{TABLE}" SET lat = ?, lon = ? WHERE id = ?', (*cache[key], row_id)
                )
                conn.commit()
            print(f"[{i}/{len(rows)}] {address}, {district} -> {cache[key]}")

        missing = conn.execute(f'SELECT COUNT(*) FROM "{TABLE}" WHERE lat IS NULL').fetchone()[0]
        print(f"Nadal bez współrzędnych: {missing}")


def main() -> None:
    if "--retry-missing" in sys.argv:
        retry_missing()
        return
    records = extract()
    print(f"Pobrano {len(records)} rekordów")
    geocode_records(records)
    load(records)
    found = sum(r["lat"] is not None for r in records)
    print(f"Zapisano {len(records)} rekordów do {DB_PATH} (zgeokodowano {found})")


if __name__ == "__main__":
    main()
