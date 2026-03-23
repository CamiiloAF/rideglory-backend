import uuid

from services.vehicles.app.domain.entities.vehicle import Vehicle
from services.vehicles.app.domain.repositories.vehicle_repository import (
    VehicleRepository,
)


class CreateVehicleUseCase:
    def __init__(self, vehicle_repository: VehicleRepository) -> None:
        self._vehicle_repository = vehicle_repository

    def execute(self, plate: str, brand: str) -> Vehicle:
        vehicle = Vehicle(id=str(uuid.uuid4()), plate=plate, brand=brand)
        return self._vehicle_repository.save(vehicle)
