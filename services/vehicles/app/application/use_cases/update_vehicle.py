from services.vehicles.app.domain.entities.vehicle import UpdateVehicle, Vehicle
from services.vehicles.app.domain.repositories.vehicle_repository import (
    VehicleRepository,
)


class UpdateVehicleUseCase:
    """Use case for updating a vehicle."""

    def __init__(self, vehicle_repository: VehicleRepository) -> None:
        self._vehicle_repository = vehicle_repository

    def execute(self, vehicle_id: str, vehicle: UpdateVehicle) -> Vehicle:
        return self._vehicle_repository.update_vehicle(vehicle_id, vehicle)
