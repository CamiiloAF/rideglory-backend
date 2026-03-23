from services.vehicles.app.application.use_cases.create_vehicle import (
    CreateVehicleUseCase,
)
from services.vehicles.app.application.use_cases.get_vehicles_by_user_id import GetVehiclesByUserIdUseCase
from services.vehicles.app.infrastructure.repositories.in_memory_vehicle_repository import (
    VehicleRepositoryImpl,
)

_repository = VehicleRepositoryImpl()


def get_create_vehicle_use_case() -> CreateVehicleUseCase:
    return CreateVehicleUseCase(vehicle_repository=_repository)

def get_get_vehicles_by_user_id_use_case() -> GetVehiclesByUserIdUseCase:
    return GetVehiclesByUserIdUseCase(vehicle_repository=_repository)