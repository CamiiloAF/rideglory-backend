from typing import Any
from fastapi import APIRouter

from apps.api_gateway.core.proxy import forward_request
from apps.api_gateway.core.settings import VEHICLES_SERVICE_BASE_URL


router = APIRouter(prefix="/api/v1/vehicles", tags=["vehicles-gateway"])

@router.post("")
async def create_vehicle(payload: dict[str, Any]):
    return await forward_request(
        method="POST",
        base_url=VEHICLES_SERVICE_BASE_URL,
        path="/api/v1/vehicles",
        json_body=payload,
    )

@router.get("/{user_id}")
async def get_vehicles_by_user_id(user_id: str):
    return await forward_request(
        method="GET",
        base_url=VEHICLES_SERVICE_BASE_URL,
        path=f"/api/v1/vehicles/{user_id}",
    )