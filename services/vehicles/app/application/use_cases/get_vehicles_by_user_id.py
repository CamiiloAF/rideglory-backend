from services.vehicles.app.domain.entities.vehicle import Vehicle
from services.vehicles.app.domain.repositories.vehicle_repository import (
    VehicleRepository,
)


class GetVehiclesByUserIdUseCase:
    """Use case for getting vehicles by user ID."""

    def __init__(self, vehicle_repository: VehicleRepository) -> None:
        self._vehicle_repository = vehicle_repository

    def execute(self, user_id: str) -> list[Vehicle]:
        return self._vehicle_repository.get_vehicles_by_user_id(user_id)
