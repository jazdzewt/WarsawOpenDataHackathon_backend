from fastapi import APIRouter

from app.api.routes import auth, health, report

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(report.router, prefix="/report", tags=["report"])
