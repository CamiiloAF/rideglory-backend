import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Response

app = FastAPI(title="Rideglory API Gateway")
VEHICLES_SERVICE_BASE_URL = os.getenv("VEHICLES_SERVICE_BASE_URL", "http://localhost:8001")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/services")
async def services_health() -> dict[str, Any]:
    services: dict[str, dict[str, Any]] = {
        "api_gateway": {"status": "ok"},
        "vehicles_service": {"status": "unknown"},
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{VEHICLES_SERVICE_BASE_URL}/health")

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


@app.post("/api/v1/vehicles")
async def create_vehicle_proxy(payload: dict[str, Any]) -> Response:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{VEHICLES_SERVICE_BASE_URL}/api/v1/vehicles",
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Vehicles service unavailable: {exc}",
        ) from exc

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type", "application/json"),
    )


@app.get("/api/v1/vehicles/{user_id}")
async def get_vehicles_by_user_id_proxy(user_id: str) -> Response:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{VEHICLES_SERVICE_BASE_URL}/api/v1/vehicles/{user_id}",
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Vehicles service unavailable: {exc}",
        ) from exc

    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type", "application/json"),
    )
