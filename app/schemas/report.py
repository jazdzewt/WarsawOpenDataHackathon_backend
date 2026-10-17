from datetime import date as Date
from datetime import datetime

from pydantic import BaseModel, Field


class ReportRequest(BaseModel):
    home_address: str = Field(..., min_length=3, max_length=200, examples=["Marszałkowska 10"])
    work_address: str = Field(..., min_length=3, max_length=200, examples=["Domaniewska 39"])
    date: Date | None = Field(default=None, description="Dzień, dla którego szukać zajęć i godzin boisk; domyślnie dziś")
    radius_km: float = Field(default=2.0, gt=0, le=20, description="Promień wyszukiwania zajęć")
    limit: int = Field(default=10, ge=1, le=50, description="Maks. liczba boisk i zajęć na lokalizację")


class Weather(BaseModel):
    station: str
    distance_km: float
    measured_at: str | None
    air_temp: float | None
    surface_temp: float | None
    humidity: float | None
    wind_speed: float | None
    wind_direction: float | None
    precipitation: float | None


class AirMeasurement(BaseModel):
    code: str
    name: str | None
    value: float | None
    unit: str | None
    index: str | None


class AirQuality(BaseModel):
    station: str
    distance_km: float
    index: str | None
    recommendations: str | None
    measurements: list[AirMeasurement]


class OutdoorVerdict(BaseModel):
    suitable: bool | None = Field(description="None, gdy brak danych o pogodzie i powietrzu")
    reasons: list[str]


class Pitch(BaseModel):
    name: str | None
    address: str
    district: str
    types: list[str]
    hours: str
    notes: str | None


class Activity(BaseModel):
    title: str
    categories: list[str]
    district: str | None
    address: str | None
    distance_km: float | None
    days: list[str]
    time: str | None
    dedicated: list[str]
    url: str | None
    description: str | None


class LocationReport(BaseModel):
    address: str
    resolved_address: str
    lat: float
    lon: float
    district: str | None
    weather: Weather | None
    air_quality: AirQuality | None
    outdoor: OutdoorVerdict
    pitches: list[Pitch]
    activities: list[Activity]


class Report(BaseModel):
    generated_at: datetime
    date: Date
    home: LocationReport
    work: LocationReport
    errors: list[str] = Field(description="Źródła danych, których nie udało się pobrać")
