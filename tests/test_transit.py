import sys
from pathlib import Path

# plan.py leży w katalogu transit/ i importuje prepare.py z tego samego katalogu,
# więc dokładamy go do sys.path. Testy nie czytają prawdziwego rozkładu GTFS.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "transit"))

import plan  # noqa: E402

# Trzy przystanki na jednej prostej: Alfa, Beta, Gamma (od najbliższego punktu startu).
STOPS = [
    {"name": "Alfa", "code": "01", "lat": 52.2000, "lon": 21.0000},
    {"name": "Beta", "code": "02", "lat": 52.2100, "lon": 21.0200},
    {"name": "Gamma", "code": "03", "lat": 52.2200, "lon": 21.0400},
]


def test_nearest_returns_stops_sorted_by_distance() -> None:
    # Punkt startowy leży przy Alfie, więc kolejność to Alfa, Beta, Gamma.
    found = plan.nearest(52.2000, 21.0000, STOPS, 3)
    assert [i for i, _, _ in found] == [0, 1, 2]
    distances = [d for _, _, d in found]
    assert distances == sorted(distances)
    assert distances[0] == 0


def test_nearest_respects_limit() -> None:
    assert len(plan.nearest(52.2000, 21.0000, STOPS, 2)) == 2


def test_nearest_walk_time_matches_distance() -> None:
    _, walk, d = plan.nearest(52.2100, 21.0200, STOPS, 1)[0]  # Beta leży dokładnie w punkcie
    assert d == 0
    assert walk == 0


def test_lines_at_lists_lines_departing_from_stop() -> None:
    data = {
        "trips": {
            0: ("1", 0, "Gamma"),  # tramwaj 1
            1: ("523", 3, "Stare Bemowo"),  # autobus 523
        },
        "connections": [
            # kurs 0: dwa przejazdy z Alfy (różne przystanki docelowe) i jeden z Bety
            (28800, 28900, 0, 1, 0),
            (28900, 29000, 0, 2, 0),
            (29000, 29100, 1, 2, 0),
            (28850, 28950, 0, 1, 1),  # autobus 523 z Alfy
        ],
    }
    lines = plan.lines_at(data, [0, 1])
    # Ten sam kurs liczy się raz, mimo że odjeżdża z Alfy dwa razy.
    assert lines[0] == {("Tramwaj", "1"), ("Autobus", "523")}
    assert lines[1] == {("Tramwaj", "1")}


def test_lines_at_ignores_stops_not_requested() -> None:
    data = {
        "trips": {0: ("1", 0, "Gamma")},
        "connections": [(28800, 28900, 0, 1, 0)],
    }
    assert 0 not in plan.lines_at(data, [2])
