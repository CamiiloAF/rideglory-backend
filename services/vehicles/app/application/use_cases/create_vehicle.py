from services.vehicles.app.domain.entities.vehicle import CreateVehicle, Vehicle
from services.vehicles.app.domain.repositories.vehicle_repository import (
    VehicleRepository,
)


class CreateVehicleUseCase:
    """Use case for creating a vehicle."""

    def __init__(self, vehicle_repository: VehicleRepository) -> None:
        self._vehicle_repository = vehicle_repository

    def execute(self, vehicle: CreateVehicle) -> Vehicle:
        return self._vehicle_repository.create_vehicle(vehicle)
