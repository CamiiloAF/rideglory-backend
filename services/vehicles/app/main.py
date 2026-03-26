from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.vehicles.app.api.v1.routes.vehicles import router as vehicles_router
from services.vehicles.app.infrastructure.models.vehicle import VehicleModel
from shared.infrastructure.database.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine, tables=[VehicleModel.__table__])
    yield


app = FastAPI(title="Vehicles Service", lifespan=lifespan)
app.include_router(vehicles_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
