from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from apps.api_gateway.core.http_client import build_http_client, close_http_client
from apps.api_gateway.core.settings import VEHICLES_SERVICE_BASE_URL
from apps.api_gateway.routes.vehicles import router as vehicles_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = build_http_client()
    try:
        yield
    finally:
        await close_http_client(app.state.http_client)


app = FastAPI(title="Rideglory API Gateway", lifespan=lifespan)

app.include_router(vehicles_router)

@app.get("/api/health/services")
async def services_health() -> dict[str, Any]:
    services: dict[str, dict[str, Any]] = {
        "api_gateway": {"status": "ok"},
        "vehicles_service": {"status": "unknown"},
    }

    try:
        response = await app.state.http_client.get(f"{VEHICLES_SERVICE_BASE_URL}/health")

        services["vehicles_service"] = {
            "status": "ok" if response.status_code == 200 else "unhealthy",
            "http_status": response.status_code,
        }
    except httpx.HTTPError as exc:
        services["vehicles_service"] = {"status": "unreachable", "error": str(exc)}

    overall_status = (
        "ok"
        if services["vehicles_service"]["status"] == "ok"
        else "degraded"
    )
    return {"status": overall_status, "services": services}

