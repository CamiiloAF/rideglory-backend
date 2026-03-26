from typing import Annotated

from fastapi import APIRouter, Depends, Path

from services.vehicles.app.application.use_cases.create_vehicle import (
    CreateVehicleUseCase,
)
from services.vehicles.app.application.use_cases.get_vehicles_by_user_id import (
    GetVehiclesByUserIdUseCase,
)
from services.vehicles.app.application.use_cases.update_vehicle import (
    UpdateVehicleUseCase,
)
from services.vehicles.app.dependencies.container import (
    get_create_vehicle_use_case,
    get_get_vehicles_by_user_id_use_case,
    get_update_vehicle_use_case,
)
from services.vehicles.app.domain.entities.vehicle import (
    CreateVehicle,
    UpdateVehicle,
    Vehicle,
)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.post("", response_model=Vehicle)
async def create_vehicle(
    request: CreateVehicle,
    use_case: CreateVehicleUseCase = Depends(get_create_vehicle_use_case),
) -> Vehicle:
    return use_case.execute(request)


@router.get("/{user_id}", response_model=list[Vehicle])
async def get_vehicles_by_user_id(
    use_case: Annotated[
        GetVehiclesByUserIdUseCase, Depends(get_get_vehicles_by_user_id_use_case)
    ],
    user_id: Annotated[str, Path(description="The ID of the user")],
) -> list[Vehicle]:
    return use_case.execute(user_id)


@router.put("/{vehicle_id}", response_model=Vehicle)
async def update_vehicle(
    request: UpdateVehicle,
    use_case: Annotated[UpdateVehicleUseCase, Depends(get_update_vehicle_use_case)],
    vehicle_id: Annotated[str, Path(description="The ID of the vehicle")],
) -> Vehicle:
    return use_case.execute(vehicle_id, request)
