from fastapi import FastAPI

from services.vehicles.app.api.v1.routes.vehicles import router as vehicles_router

app = FastAPI(title="Vehicles Service")
app.include_router(vehicles_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
