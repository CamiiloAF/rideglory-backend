from fastapi import Depends
from sqlalchemy.orm import Session

from services.vehicles.app.application.use_cases.create_vehicle import (
    CreateVehicleUseCase,
)
from services.vehicles.app.application.use_cases.get_vehicles_by_user_id import (
    GetVehiclesByUserIdUseCase,
)
from services.vehicles.app.application.use_cases.update_vehicle import (
    UpdateVehicleUseCase,
)
from services.vehicles.app.infrastructure.repositories.vehicle_repository import (
    VehicleRepositoryImpl,
)
from shared.infrastructure.database.database import get_db


def get_vehicle_repository(db: Session = Depends(get_db)) -> VehicleRepositoryImpl:
    return VehicleRepositoryImpl(db=db)


def get_create_vehicle_use_case(
    repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
) -> CreateVehicleUseCase:
    return CreateVehicleUseCase(vehicle_repository=repository)


def get_get_vehicles_by_user_id_use_case(
    repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
) -> GetVehiclesByUserIdUseCase:
    return GetVehiclesByUserIdUseCase(vehicle_repository=repository)


def get_update_vehicle_use_case(
    repository: VehicleRepositoryImpl = Depends(get_vehicle_repository),
) -> UpdateVehicleUseCase:
    return UpdateVehicleUseCase(vehicle_repository=repository)
