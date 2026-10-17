from datetime import date, datetime

from fastapi import APIRouter, HTTPException, status

from app.schemas.report import Report, ReportRequest
from app.services import geocoding
from app.services.report_service import CityData, build_location_report
from app.services.um_api import UmApiError, um_api

router = APIRouter()


def _fetch_city_data() -> tuple[CityData, list[str]]:
    data = CityData()
    errors = []
    for name in ("pogoda", "powietrze", "boiska", "zajecia"):
        try:
            setattr(data, name, getattr(um_api, name)())
        except UmApiError as exc:
            errors.append(f"Nie udało się pobrać danych '{name}': {exc}")
    return data, errors


def _geocode(address: str, label: str) -> geocoding.GeoPoint:
    try:
        point = geocoding.geocode_address(address)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Błąd geokodowania ({label}): {exc}") from exc
    if point is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Nie znaleziono adresu ({label}) w Warszawie: {address}")
    return point


@router.post("", response_model=Report, summary="Pogoda, powietrze, boiska i zajęcia przy domu i pracy")
def create_report(payload: ReportRequest) -> Report:
    home = _geocode(payload.home_address, "dom")
    work = _geocode(payload.work_address, "praca")
    data, errors = _fetch_city_data()
    day = payload.date or date.today()
    args = (data, day, payload.radius_km, payload.limit)
    return Report(
        generated_at=datetime.now(),
        date=day,
        home=build_location_report(payload.home_address, home, *args),
        work=build_location_report(payload.work_address, work, *args),
        errors=errors,
    )
