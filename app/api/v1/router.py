from fastapi import APIRouter

from app.api.v1 import auth, availability, stations

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(stations.router)
api_router.include_router(availability.router)
