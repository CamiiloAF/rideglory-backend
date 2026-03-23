from typing import Annotated
from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel

from services.vehicles.app.application.use_cases.create_vehicle import (
    CreateVehicleUseCase,
)
from services.vehicles.app.application.use_cases.get_vehicles_by_user_id import GetVehiclesByUserIdUseCase
from services.vehicles.app.dependencies.container import get_create_vehicle_use_case, get_get_vehicles_by_user_id_use_case
from services.vehicles.app.domain.entities.vehicle import Vehicle

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


class CreateVehicleRequest(BaseModel):
    plate: str
    brand: str


class CreateVehicleResponse(BaseModel):
    id: str
    plate: str
    brand: str


class GetVehiclesByUserIdResponse(BaseModel):
    vehicles: list[Vehicle]


@router.post("", response_model=CreateVehicleResponse)
async def create_vehicle(
    request: CreateVehicleRequest,
    use_case: CreateVehicleUseCase = Depends(get_create_vehicle_use_case),
) -> CreateVehicleResponse:
    vehicle = use_case.execute(plate=request.plate, brand=request.brand)
    return CreateVehicleResponse(
        id=vehicle.id,
        plate=vehicle.plate,
        brand=vehicle.brand,
    )

@router.get("/{user_id}", response_model=GetVehiclesByUserIdResponse)
async def get_vehicles_by_user_id(
    use_case: GetVehiclesByUserIdUseCase = Depends(get_get_vehicles_by_user_id_use_case),
    user_id: str = Annotated[str, Path(description="The ID of the user")]
) -> GetVehiclesByUserIdResponse:
    vehicles = use_case.execute(user_id)
    return GetVehiclesByUserIdResponse(vehicles=vehicles)