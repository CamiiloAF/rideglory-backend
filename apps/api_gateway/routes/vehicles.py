"""HTTP routes that proxy the vehicles API to the vehicles microservice."""

from http import HTTPMethod

from fastapi import APIRouter, Request

from apps.api_gateway.core.proxy import forward_request
from apps.api_gateway.core.proxy_types import ForwardRequestParams
from apps.api_gateway.core.settings import VEHICLES_SERVICE_BASE_URL
from services.vehicles.app.domain.entities.vehicle import CreateVehicle, UpdateVehicle

gateway_router = APIRouter(prefix="/api/v1/vehicles", tags=["vehicles-gateway"])


@gateway_router.post("")
async def create_vehicle(request: Request, payload: CreateVehicle):
    """Proxy POST to vehicles service: create a vehicle."""
    return await forward_request(
        request=request,
        params=ForwardRequestParams(
            method=HTTPMethod.POST,
            base_url=VEHICLES_SERVICE_BASE_URL,
            path="/api/v1/vehicles",
            body=payload,
        ),
    )


@gateway_router.put("/{vehicle_id}")
async def update_vehicle(request: Request, vehicle_id: str, payload: UpdateVehicle):
    """Proxy PUT to vehicles service: update a vehicle by id."""
    return await forward_request(
        request=request,
        params=ForwardRequestParams(
            method=HTTPMethod.PUT,
            base_url=VEHICLES_SERVICE_BASE_URL,
            path=f"/api/v1/vehicles/{vehicle_id}",
            body=payload,
        ),
    )


@gateway_router.get("/{user_id}")
async def get_vehicles_by_user_id(request: Request, user_id: str):
    """Proxy GET to vehicles service: list vehicles for a user."""
    return await forward_request(
        request=request,
        params=ForwardRequestParams(
            method=HTTPMethod.GET,
            base_url=VEHICLES_SERVICE_BASE_URL,
            path=f"/api/v1/vehicles/{user_id}",
        ),
    )
