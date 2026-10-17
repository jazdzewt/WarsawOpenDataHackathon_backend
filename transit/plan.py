"""Planer najszybszych przejazdów komunikacją miejską w Warszawie.

Algorytm: Connection Scan Algorithm (CSA) na rozkładzie GTFS.

Przykłady:
    python plan.py "Centrum" "Wilanów"
    python plan.py "52.2297,21.0122" "52.1650,21.0880" --time 8:15
    python plan.py "Plac Zbawiciela" "Lotnisko Chopina" --time 17:30 -n 5
    python plan.py "ul. Puławska 145" "Pałac Kultury i Nauki"   # adres -> Nominatim (OSM)
    python plan.py "Pl. Politechniki" --nearest 5              # najbliższe przystanki + linie
"""
import argparse
import json
import math
import sys
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime

from prepare import haversine, load, walk_seconds

MAX_ACCESS_WALK = 1000  # m, dojście z punktu startu / do celu
CHANGE_TIME = 90        # s, minimalny czas na przesiadkę
INF = float("inf")

MODE = {0: "Tramwaj", 1: "Metro", 2: "Pociąg", 3: "Autobus"}


# ---------- rozpoznawanie punktów A/B ----------

def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c)).replace("ł", "l").strip()


def geocode(text):
    q = urllib.parse.urlencode({"q": f"{text}, Warszawa", "format": "json", "limit": 1})
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{q}",
        headers={"User-Agent": "warsaw-transit-planner-prototype/0.1"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.load(r)
    if not res:
        return None
    return float(res[0]["lat"]), float(res[0]["lon"]), res[0]["display_name"].split(",")[0]


def resolve(text, stops):
    """Zwraca (lat, lon, opis). Akceptuje 'lat,lon', nazwę przystanku albo adres."""
    parts = text.replace(" ", "").split(",")
    if len(parts) == 2:
        try:
            return float(parts[0]), float(parts[1]), text
        except ValueError:
            pass
    q = norm(text)
    exact = [s for s in stops if norm(s["name"]) == q]
    if exact:
        lat = sum(s["lat"] for s in exact) / len(exact)
        lon = sum(s["lon"] for s in exact) / len(exact)
        return lat, lon, f"przystanek {exact[0]['name']}"
    hit = geocode(text)
    if hit:
        return hit
    partial = sorted({s["name"] for s in stops if q in norm(s["name"])})
    if partial:
        sys.exit(f"Nie znaleziono '{text}'. Czy chodziło o: {', '.join(partial[:10])}?")
    sys.exit(f"Nie znaleziono '{text}'.")


def nearby(lat, lon, stops, radius):
    out = []
    for i, s in enumerate(stops):
        if abs(s["lat"] - lat) > 0.02 or abs(s["lon"] - lon) > 0.03:
            continue
        d = haversine(lat, lon, s["lat"], s["lon"])
        if d <= radius:
            out.append((i, walk_seconds(d), d))
    return out


def nearest(lat, lon, stops, n):
    """Zwraca n najbliższych przystanków jako listę (indeks, czas pieszo w s, odległość w m)."""
    ranked = sorted(
        ((i, haversine(lat, lon, s["lat"], s["lon"])) for i, s in enumerate(stops)),
        key=lambda item: item[1],
    )[:n]
    return [(i, walk_seconds(d), d) for i, d in ranked]


def lines_at(data, stop_ids):
    """Linie odjeżdżające z podanych przystanków tego dnia.

    Zwraca słownik indeks przystanku -> zbiór par (rodzaj pojazdu, numer linii).
    Liczymy na podstawie połączeń, więc uwzględniamy tylko kursy aktywne w wybranym dniu.
    """
    wanted = set(stop_ids)
    out = defaultdict(set)
    trips = data["trips"]
    for _, _, u, _, t in data["connections"]:
        if u in wanted:
            line, rtype, _ = trips[t]
            out[u].add((MODE.get(rtype, "Linia"), line))
    return out


# ---------- CSA ----------

def csa(data, origin, dest, t0, start_idx):
    """Najwcześniejszy przyjazd. Zwraca listę odcinków podróży albo None."""
    stops, conns, footpaths = data["stops"], data["connections"], data["footpaths"]
    n = len(stops)
    ready = [INF] * n        # od kiedy można wsiąść na przystanku
    ready_ptr = [None] * n   # ('origin', walk_s) | ('ride',) | ('foot', from_stop, walk_s)
    arr = [INF] * n          # przyjazd pojazdem
    arr_ptr = [None] * n     # (conn_enter, conn_exit)
    trip_enter = {}          # trip -> indeks połączenia, w którym wsiedliśmy

    for i, w, _ in origin:
        if t0 + w < ready[i]:
            ready[i] = t0 + w
            ready_ptr[i] = ("origin", w)

    egress = {i: w for i, w, _ in dest}
    best, best_stop = INF, None

    for ci in range(start_idx, len(conns)):
        dep, a, u, v, t = conns[ci]
        if dep >= best:
            break
        if t not in trip_enter:
            if ready[u] > dep:
                continue
            trip_enter[t] = ci
        if a < arr[v]:
            arr[v] = a
            arr_ptr[v] = (trip_enter[t], ci)
            if v in egress and a + egress[v] < best:
                best, best_stop = a + egress[v], v
            if a + CHANGE_TIME < ready[v]:
                ready[v] = a + CHANGE_TIME
                ready_ptr[v] = ("ride",)
            for q, w in footpaths[v]:
                if a + w + CHANGE_TIME < ready[q]:
                    ready[q] = a + w + CHANGE_TIME
                    ready_ptr[q] = ("foot", v, w)

    if best_stop is None:
        return None

    # odtwarzanie trasy od końca
    legs = [("walk_end", best_stop, egress[best_stop])]
    stop = best_stop
    while True:
        enter, exit_ = arr_ptr[stop]
        legs.append(("ride", enter, exit_))
        board = conns[enter][2]
        p = ready_ptr[board]
        if p[0] == "origin":
            legs.append(("walk_start", board, p[1]))
            break
        if p[0] == "foot":
            legs.append(("transfer", p[1], board, p[2]))
            stop = p[1]
        else:
            stop = board
    legs.reverse()
    return legs, best


# ---------- wypisywanie ----------

def hm(sec):
    sec = int(sec)
    return f"{(sec // 3600) % 24:02d}:{(sec % 3600) // 60:02d}"


def stop_label(s):
    return f"{s['name']} {s['code']}".strip()


def describe(data, legs, arrival):
    stops, conns, trips = data["stops"], data["connections"], data["trips"]
    rides = [l for l in legs if l[0] == "ride"]
    first_dep = conns[rides[0][1]][0]
    walk0 = legs[0][2]
    leave = first_dep - walk0
    lines = []
    lines.append(f"Wyjście {hm(leave)} → cel {hm(arrival)}  "
                 f"({round((arrival - leave) / 60)} min, przesiadki: {len(rides) - 1})")
    for l in legs:
        if l[0] == "walk_start":
            lines.append(f"   🚶 {round(l[2] / 60)} min pieszo do przystanku {stop_label(stops[l[1]])}")
        elif l[0] == "ride":
            c1, c2 = conns[l[1]], conns[l[2]]
            line, rtype, headsign = trips[c1[4]]
            n_stops = sum(1 for k in range(l[1], l[2] + 1) if conns[k][4] == c1[4])
            lines.append(f"   🚍 {MODE.get(rtype, 'Linia')} {line} (kier. {headsign}): "
                         f"{stop_label(stops[c1[2]])} {hm(c1[0])} → "
                         f"{stop_label(stops[c2[3]])} {hm(c2[1])}  [{n_stops} przyst.]")
        elif l[0] == "transfer":
            lines.append(f"   🚶 {round(l[3] / 60)} min przejście do {stop_label(stops[l[2]])}")
        elif l[0] == "walk_end":
            lines.append(f"   🚶 {round(l[2] / 60)} min pieszo do celu")
    return "\n".join(lines), first_dep, leave


def show_nearest(data, origin, n):
    """Wypisuje n najbliższych przystanków od punktu origin wraz z liniami, które stamtąd odjeżdżają."""
    stops = data["stops"]
    found = nearest(origin[0], origin[1], stops, n)
    lines = lines_at(data, [i for i, _, _ in found])
    print(f"Najbliższe przystanki od: {origin[2]}\n")
    for k, (i, walk, d) in enumerate(found, 1):
        served = ", ".join(f"{mode} {line}" for mode, line in sorted(lines[i])) or "brak połączeń tego dnia"
        print(f"{k}. {stop_label(stops[i])} - {round(d)} m (ok. {max(1, round(walk / 60))} min pieszo)")
        print(f"   {served}\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Najszybsze przejazdy komunikacją w Warszawie")
    ap.add_argument("start")
    ap.add_argument("cel", nargs="?", help="punkt docelowy (niepotrzebny przy --nearest)")
    ap.add_argument("--time", help="godzina wyjazdu HH:MM (domyślnie teraz)")
    ap.add_argument("--date", help="data YYYY-MM-DD (domyślnie dziś)")
    ap.add_argument("-n", type=int, default=3, help="ile wariantów pokazać")
    ap.add_argument("--nearest", type=int, metavar="N",
                    help="zamiast trasy pokaż N najbliższych przystanków od startu")
    args = ap.parse_args()

    d = date.fromisoformat(args.date) if args.date else date.today()
    if args.time:
        h, m = map(int, args.time.split(":"))
    else:
        now = datetime.now()
        h, m = now.hour, now.minute
    t0 = h * 3600 + m * 60

    data = load(d)
    stops, conns = data["stops"], data["connections"]

    a = resolve(args.start, stops)
    if args.nearest:
        show_nearest(data, a, args.nearest)
        return
    if not args.cel:
        sys.exit("Podaj punkt docelowy albo użyj --nearest N.")
    b = resolve(args.cel, stops)
    print(f"Z: {a[2]}  →  Do: {b[2]}   ({d}, od {hm(t0)})\n")

    direct = haversine(a[0], a[1], b[0], b[1])
    origin = nearby(a[0], a[1], stops, MAX_ACCESS_WALK)
    dest = nearby(b[0], b[1], stops, MAX_ACCESS_WALK)
    if not origin or not dest:
        sys.exit("Brak przystanków w promieniu 1 km od startu lub celu.")

    import bisect
    deps = [c[0] for c in conns]
    cands, t, seen = [], t0, set()
    for _ in range(args.n * 3):
        res = csa(data, origin, dest, t, bisect.bisect_left(deps, t))
        if not res:
            break
        legs, arrival = res
        text, first_dep, leave = describe(data, legs, arrival)
        key = tuple((l[1], l[2]) for l in legs if l[0] == "ride")
        if key not in seen:
            seen.add(key)
            cands.append((leave, arrival, text))
        t = leave + 60  # następny wariant: wyjście co najmniej minutę później

    # odrzuć warianty zdominowane (wyjście wcześniej, a przyjazd nie wcześniej)
    best = [c for c in cands
            if not any(o is not c and o[0] >= c[0] and o[1] <= c[1] for o in cands)]
    best = sorted(best)[:args.n]
    found = len(best)
    for k, (_, _, text) in enumerate(best, 1):
        print(f"{k}. {text}\n")

    walk_min = round(walk_seconds(direct) / 60)
    if walk_min <= 30:
        print(f"Pieszo całą drogę: ok. {walk_min} min")
    if found == 0:
        print("Nie znaleziono połączenia.")


if __name__ == "__main__":
    main()
