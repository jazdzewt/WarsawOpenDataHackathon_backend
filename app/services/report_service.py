"""Łączy dane pogodowe, jakość powietrza, boiska i zajęcia sportowe dla wskazanych punktów."""

import html
import math
import re
from dataclasses import dataclass, field
from datetime import date as Date

from app.schemas.report import (
    Activity,
    AirMeasurement,
    AirQuality,
    LocationReport,
    OutdoorVerdict,
    Pitch,
    Weather,
)
from app.services.geocoding import GeoPoint

WEEKDAY_IDS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKDAY_PL = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
BAD_AIR = {"Dostateczny", "Zły", "Bardzo zły"}


@dataclass
class CityData:
    """Surowe odpowiedzi API; pusta lista, jeśli źródła nie udało się pobrać."""

    pogoda: list[dict] = field(default_factory=list)
    powietrze: list[dict] = field(default_factory=list)
    boiska: list[dict] = field(default_factory=list)
    zajecia: list[dict] = field(default_factory=list)


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _norm(text: str | None) -> str:
    return (text or "").strip().casefold()


def _to_float(value) -> float | None:
    """API zwraca liczby raz jako number, raz jako string (także z przecinkiem)."""
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _nearest(point: GeoPoint, records: list[dict]) -> tuple[dict, float] | None:
    best = None
    for rec in records:
        lat, lon = _to_float(rec.get("lat")), _to_float(rec.get("lon"))
        if lat is None or lon is None:
            continue
        d = distance_km(point.lat, point.lon, lat, lon)
        if best is None or d < best[1]:
            best = (rec, d)
    return best


def _activity_point(rec: dict) -> tuple[float, float, str | None] | None:
    for feature in (rec.get("map") or {}).get("features", []):
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates")
        if geometry.get("type") == "Point" and coords and len(coords) >= 2:
            lat, lon = _to_float(coords[1]), _to_float(coords[0])
            if lat is not None and lon is not None:
                return lat, lon, (feature.get("properties") or {}).get("district")
    return None


def _activity_districts(rec: dict) -> list[str]:
    names = [loc["name"] for loc in rec.get("localization", []) if loc.get("name")]
    point = _activity_point(rec)
    if point and point[2]:
        names.append(point[2])
    return names


def _clean_html(text: str | None, max_len: int = 300) -> str | None:
    if not text:
        return None
    plain = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()
    return plain if len(plain) <= max_len else plain[: max_len - 1].rstrip() + "…"


def resolve_district(point: GeoPoint, data: CityData) -> str | None:
    """Dzielnica z geokodera, jeśli pasuje do nazw z danych miejskich;
    w przeciwnym razie dzielnica najbliższego punktu z danymi."""
    known = {_norm(r.get("Dzielnica")): r["Dzielnica"] for r in data.boiska if r.get("Dzielnica")}
    for rec in data.zajecia:
        for name in _activity_districts(rec):
            known.setdefault(_norm(name), name)
    if point.district and (not known or _norm(point.district) in known):
        return known.get(_norm(point.district), point.district)

    candidates = []
    for rec in data.zajecia:
        p = _activity_point(rec)
        if p and p[2]:
            candidates.append({"lat": p[0], "lon": p[1], "district": p[2]})
    for rec in data.powietrze:
        district = (rec.get("address") or {}).get("district")
        if district:
            candidates.append({"lat": rec.get("lat"), "lon": rec.get("lon"), "district": district})
    nearest = _nearest(point, candidates)
    return nearest[0]["district"] if nearest else point.district


def build_weather(point: GeoPoint, pogoda: list[dict]) -> Weather | None:
    nearest = _nearest(point, pogoda)
    if not nearest:
        return None
    rec, dist = nearest
    return Weather(
        station=rec.get("lokalizacja", "?"),
        distance_km=round(dist, 2),
        measured_at=rec.get("czas"),
        air_temp=rec.get("temp_pow"),
        surface_temp=rec.get("temp_naw"),
        humidity=rec.get("wilg_pow"),
        wind_speed=rec.get("pred_wiatru"),
        wind_direction=rec.get("kier_wiatru"),
        precipitation=rec.get("int_opadu"),
    )


def build_air_quality(point: GeoPoint, powietrze: list[dict]) -> AirQuality | None:
    # Tylko stacje z wyliczonym ogólnym indeksem jakości powietrza
    with_index = [r for r in powietrze if (r.get("ijp") or {}).get("name")]
    nearest = _nearest(point, with_index)
    if not nearest:
        return None
    rec, dist = nearest
    return AirQuality(
        station=rec.get("name") or rec.get("station") or "?",
        distance_km=round(dist, 2),
        index=rec["ijp"]["name"],
        recommendations=rec["ijp"].get("recommendations"),
        measurements=[
            AirMeasurement(
                code=m["param_code"],
                name=m.get("param_name"),
                value=m.get("value"),
                unit=m.get("unit"),
                index=(m.get("ijp") or {}).get("name"),
            )
            for m in rec.get("data", [])
            if m.get("param_code")
        ],
    )


def build_outdoor_verdict(weather: Weather | None, air: AirQuality | None) -> OutdoorVerdict:
    if weather is None and air is None:
        return OutdoorVerdict(suitable=None, reasons=["Brak danych o pogodzie i jakości powietrza"])
    reasons = []
    if air and air.index in BAD_AIR:
        reasons.append(f"Jakość powietrza: {air.index}")
    if weather:
        if weather.precipitation:
            reasons.append(f"Opady ({weather.precipitation} mm/h)")
        if weather.air_temp is not None and weather.air_temp < 0:
            reasons.append(f"Mróz ({weather.air_temp}°C)")
        if weather.air_temp is not None and weather.air_temp > 30:
            reasons.append(f"Upał ({weather.air_temp}°C)")
        if weather.wind_speed is not None and weather.wind_speed > 10:
            reasons.append(f"Silny wiatr ({weather.wind_speed} m/s)")
    if reasons:
        return OutdoorVerdict(suitable=False, reasons=reasons)
    return OutdoorVerdict(suitable=True, reasons=["Dobre warunki do aktywności na zewnątrz"])


def build_pitches(district: str | None, boiska: list[dict], day: Date, limit: int) -> list[Pitch]:
    """Boiska w dzielnicy otwarte w danym dniu, zgrupowane po adresie obiektu."""
    if not district:
        return []
    day_key = WEEKDAY_PL[day.weekday()]
    grouped: dict[tuple[str, str], Pitch] = {}
    for rec in boiska:
        if _norm(rec.get("Dzielnica")) != _norm(district):
            continue
        hours = (rec.get(day_key) or "").strip()
        if not hours or hours == "-":
            continue
        address = rec.get("Adres obiektu") or "?"
        key = (address, hours)
        pitch = grouped.get(key)
        if pitch is None:
            pitch = grouped[key] = Pitch(
                name=rec.get("Nazwa placówki oświatowej"),
                address=address,
                district=rec["Dzielnica"],
                types=[],
                hours=hours,
                notes=rec.get("Uwagi"),
            )
        obj_type = rec.get("Typ obiektu")
        if obj_type and obj_type not in pitch.types:
            pitch.types.append(obj_type)
    return list(grouped.values())[:limit]


def _activity_on_day(rec: dict, day: Date) -> bool:
    day_ids = {d["id"] for d in rec.get("day", []) if d.get("id")}
    if day_ids:
        return WEEKDAY_IDS[day.weekday()] in day_ids
    dates = rec.get("date") or []
    if dates:
        return day.isoformat() in dates
    return True  # brak informacji o terminie — nie odrzucamy


def build_activities(
    point: GeoPoint, district: str | None, zajecia: list[dict], day: Date, radius_km: float, limit: int
) -> list[Activity]:
    """Zajęcia w danym dniu w promieniu radius_km; zajęcia bez współrzędnych — po dzielnicy."""
    found: list[Activity] = []
    for rec in zajecia:
        if not _activity_on_day(rec, day):
            continue
        districts = _activity_districts(rec)
        p = _activity_point(rec)
        dist = distance_km(point.lat, point.lon, p[0], p[1]) if p else None
        if dist is not None:
            if dist > radius_km:
                continue
        elif not district or _norm(district) not in {_norm(d) for d in districts}:
            continue

        addresses = rec.get("address") or []
        address = None
        if addresses:
            a = addresses[0]
            address = ", ".join(x for x in (a.get("name"), a.get("street")) if x) or None
        found.append(
            Activity(
                title=rec.get("title") or "?",
                categories=[c["name"] for c in rec.get("category", []) if c.get("name")],
                district=districts[0] if districts else None,
                address=address,
                distance_km=round(dist, 2) if dist is not None else None,
                days=[d["name"] for d in rec.get("day", []) if d.get("name")],
                time=rec.get("time"),
                dedicated=[d["name"] for d in rec.get("dedicated", []) if d.get("name")],
                url=rec.get("url"),
                description=_clean_html(rec.get("text")),
            )
        )
    found.sort(key=lambda a: (a.distance_km is None, a.distance_km or 0))
    return found[:limit]


def build_location_report(
    address: str, point: GeoPoint, data: CityData, day: Date, radius_km: float, limit: int
) -> LocationReport:
    district = resolve_district(point, data)
    weather = build_weather(point, data.pogoda)
    air = build_air_quality(point, data.powietrze)
    return LocationReport(
        address=address,
        resolved_address=point.display_name,
        lat=point.lat,
        lon=point.lon,
        district=district,
        weather=weather,
        air_quality=air,
        outdoor=build_outdoor_verdict(weather, air),
        pitches=build_pitches(district, data.boiska, day, limit),
        activities=build_activities(point, district, data.zajecia, day, radius_km, limit),
    )
