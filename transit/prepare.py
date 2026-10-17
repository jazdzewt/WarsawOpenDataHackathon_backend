"""Przygotowanie danych GTFS (ZTM Warszawa) dla plan.py.

Z plików w katalogu gtfs/ budujemy strukturę, której używa algorytm CSA:
- stops:       lista przystanków (name, code, lat, lon),
- trips:       kursy -> (numer linii, typ pojazdu, kierunek), indeksowane liczbą,
- connections: lista przejazdów między sąsiednimi przystankami
               (odjazd, przyjazd, przystanek startowy, przystanek końcowy, kurs),
               posortowana po czasie odjazdu,
- footpaths:   dla każdego przystanku - przystanki dostępne pieszo w promieniu 300 m.

Czasy są w sekundach od północy. GTFS dopuszcza godziny >= 24:00 (kursy nocne),
więc takie wartości zostawiamy bez zmian.
"""
import csv
import math
from collections import defaultdict
from datetime import date
from pathlib import Path

GTFS_DIR = Path(__file__).resolve().parent / "gtfs"
WALK_SPEED = 1.2  # m/s, prędkość marszu
FOOTPATH_RADIUS = 300  # m, maksymalna odległość przejścia między przystankami
GRID = 0.005  # stopnie (~550 m), rozmiar siatki do szukania sąsiednich przystanków

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def haversine(lat1, lon1, lat2, lon2):
    """Odległość w metrach między dwoma punktami na kuli ziemskiej."""
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def walk_seconds(distance_m):
    """Czas marszu w sekundach dla podanej odległości w metrach."""
    return distance_m / WALK_SPEED


def read_csv(name):
    """Czyta plik GTFS jako słowniki. utf-8-sig usuwa BOM, który ZTM dodaje na początku pliku."""
    with open(GTFS_DIR / name, encoding="utf-8-sig", newline="") as f:
        yield from csv.DictReader(f)


def hms_to_seconds(value):
    """'HH:MM:SS' -> sekundy od północy (HH może być >= 24)."""
    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s


def active_services(d):
    """Zbiór identyfikatorów usług (service_id) obowiązujących w dniu d.

    Najpierw reguła tygodniowa z calendar.txt, potem wyjątki z calendar_dates.txt
    (exception_type 1 = dodaj usługę, 2 = usuń usługę).
    """
    ymd = d.strftime("%Y%m%d")
    weekday = WEEKDAYS[d.weekday()]
    services = set()
    for row in read_csv("calendar.txt"):
        if row[weekday] == "1" and row["start_date"] <= ymd <= row["end_date"]:
            services.add(row["service_id"])
    for row in read_csv("calendar_dates.txt"):
        if row["date"] == ymd:
            if row["exception_type"] == "1":
                services.add(row["service_id"])
            elif row["exception_type"] == "2":
                services.discard(row["service_id"])
    return services


def load_stops():
    """Wczytuje przystanki. Zwraca (lista przystanków, słownik stop_id -> indeks)."""
    stops = []
    index = {}
    for row in read_csv("stops.txt"):
        if not row["stop_lat"] or not row["stop_lon"]:
            continue
        index[row["stop_id"]] = len(stops)
        stops.append(
            {
                "name": row["stop_name"],
                "code": row["stop_code"],
                "lat": float(row["stop_lat"]),
                "lon": float(row["stop_lon"]),
            }
        )
    return stops, index


def load_trips(services):
    """Kursy obowiązujące w danym dniu.

    Zwraca (trips, trip_index): trips to słownik indeks -> (linia, typ pojazdu, kierunek),
    trip_index to słownik trip_id -> indeks.
    """
    routes = {
        row["route_id"]: (row["route_short_name"], int(row["route_type"]))
        for row in read_csv("routes.txt")
    }
    trips = {}
    trip_index = {}
    for row in read_csv("trips.txt"):
        if row["service_id"] not in services:
            continue
        line, rtype = routes.get(row["route_id"], ("?", -1))
        trip_index[row["trip_id"]] = len(trips)
        trips[len(trips)] = (line, rtype, row["trip_headsign"])
    return trips, trip_index


def build_connections(stop_index, trip_index):
    """Buduje listę przejazdów między sąsiednimi przystankami dla aktywnych kursów.

    stop_times.txt jest czytany strumieniowo (plik ma ponad 400 MB), więc wiersze
    jednego kursu muszą być ułożone obok siebie. Jeśli nie są, zgłaszamy błąd,
    zamiast cicho zbudować błędną sieć.
    """
    connections = []
    finished = set()  # kursy, których wiersze już przetworzyliśmy
    current = None
    rows = []  # (stop_sequence, odjazd, przyjazd, indeks przystanku) bieżącego kursu

    def flush(trip_id):
        # Sortujemy po stop_sequence, bo GTFS nie gwarantuje kolejności wierszy.
        rows.sort()
        trip = trip_index[trip_id]
        for (_, _, dep_from, stop_from), (_, arr_to, _, stop_to) in zip(rows, rows[1:]):
            connections.append((dep_from, arr_to, stop_from, stop_to, trip))

    for row in read_csv("stop_times.txt"):
        trip_id = row["trip_id"]
        if trip_id not in trip_index:
            continue  # kurs nieaktywny tego dnia
        if trip_id != current:
            if current is not None:
                flush(current)
                finished.add(current)
            if trip_id in finished:
                raise ValueError(f"Wiersze kursu {trip_id} w stop_times.txt nie są pogrupowane")
            current = trip_id
            rows = []
        stop = stop_index.get(row["stop_id"])
        if stop is None or not row["arrival_time"] or not row["departure_time"]:
            continue  # brak przystanku w stops.txt albo brak czasu - pomijamy wiersz
        rows.append(
            (
                int(row["stop_sequence"]),
                hms_to_seconds(row["arrival_time"]),
                hms_to_seconds(row["departure_time"]),
                stop,
            )
        )
    if current is not None:
        flush(current)
    return connections


def build_footpaths(stops):
    """Dla każdego przystanku - lista (indeks sąsiada, czas marszu w sekundach).

    Sąsiadów szukamy w siatce, zamiast porównywać każdą parę przystanków (to byłoby
    około 24 mln obliczeń odległości dla ~7 tys. przystanków).
    """
    grid = defaultdict(list)
    for i, s in enumerate(stops):
        grid[(math.floor(s["lat"] / GRID), math.floor(s["lon"] / GRID))].append(i)

    footpaths = [[] for _ in stops]
    for i, s in enumerate(stops):
        cell_lat, cell_lon = math.floor(s["lat"] / GRID), math.floor(s["lon"] / GRID)
        for dlat in (-1, 0, 1):
            for dlon in (-1, 0, 1):
                for j in grid[(cell_lat + dlat, cell_lon + dlon)]:
                    if j == i:
                        continue
                    d = haversine(s["lat"], s["lon"], stops[j]["lat"], stops[j]["lon"])
                    if d <= FOOTPATH_RADIUS:
                        footpaths[i].append((j, walk_seconds(d)))
    return footpaths


def load(d: date):
    """Zwraca wszystkie dane potrzebne plan.py dla dnia d."""
    stops, stop_index = load_stops()
    services = active_services(d)
    trips, trip_index = load_trips(services)
    connections = build_connections(stop_index, trip_index)
    connections.sort()  # CSA wymaga przejazdów posortowanych po czasie odjazdu
    footpaths = build_footpaths(stops)
    return {
        "stops": stops,
        "trips": trips,
        "connections": connections,
        "footpaths": footpaths,
    }
