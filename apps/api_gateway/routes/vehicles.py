from http import HTTPMethod
from typing import Any
from fastapi import APIRouter, Request

from apps.api_gateway.core.proxy import forward_request
from apps.api_gateway.core.proxy_types import ForwardRequestParams
from apps.api_gateway.core.settings import VEHICLES_SERVICE_BASE_URL


router = APIRouter(prefix="/api/v1/vehicles", tags=["vehicles-gateway"])

@router.post("")
async def create_vehicle(request: Request, payload: dict[str, Any]):
    return await forward_request(
        request = request,
        params = ForwardRequestParams(
            method=HTTPMethod.POST,
            base_url=VEHICLES_SERVICE_BASE_URL,
            path="/api/v1/vehicles",
            body=payload,
        )
    )

@router.get("/{user_id}")
async def get_vehicles_by_user_id(request: Request, user_id: str):
    return await forward_request(
        request=request,
        params=ForwardRequestParams(
            method=HTTPMethod.GET,
            base_url=VEHICLES_SERVICE_BASE_URL,
            path=f"/api/v1/vehicles/{user_id}",
        )
    )