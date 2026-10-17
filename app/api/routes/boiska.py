import math
import sqlite3
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

DB_PATH = Path(__file__).resolve().parents[3] / "boiska.db"

router = APIRouter()


class Boisko(BaseModel):
    id: int
    nazwa: str
    adres: str | None
    dzielnica: str | None
    typ: str | None
    przeznaczenie: str | None
    godziny: str | None
    uwagi: str | None
    lat: float
    lon: float


def _to_float(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


@router.get("/boiska", response_model=list[Boisko], summary="Boiska do mapy")
def list_boiska() -> list[Boisko]:
    if not DB_PATH.exists():
        return []
    with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
        rows = conn.execute(
            """
            SELECT id, nazwa_placowki_oswiatowej, adres_obiektu, dzielnica, typ_obiektu,
                   boisk_uniwersalne_zawiera, poniedzialek, uwagi, lat, lon
            FROM boiska
            WHERE nazwa_placowki_oswiatowej IS NOT NULL
            ORDER BY id
            """
        ).fetchall()

    boiska = []
    for id_, nazwa, adres, dzielnica, typ, przeznaczenie, godziny, uwagi, lat, lon in rows:
        lat, lon = _to_float(lat), _to_float(lon)
        if lat is None or lon is None:
            continue
        boiska.append(
            Boisko(
                id=id_,
                nazwa=nazwa,
                adres=adres,
                dzielnica=dzielnica,
                typ=typ,
                przeznaczenie=przeznaczenie.replace("-", ", ") if przeznaczenie else None,
                godziny=godziny,
                uwagi=uwagi,
                lat=lat,
                lon=lon,
            )
        )
    return boiska
