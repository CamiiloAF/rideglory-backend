from services.vehicles.app.domain.entities.vehicle import Vehicle
from services.vehicles.app.domain.repositories.vehicle_repository import (
    VehicleRepository,
)


class VehicleRepositoryImpl(VehicleRepository):
    def __init__(self) -> None:
        self._data: dict[str, Vehicle] = {}

    def save(self, vehicle: Vehicle) -> Vehicle:
        self._data[vehicle.id] = vehicle
        return vehicle

    def getVehiclesByUserId(self, user_id: str) -> list[Vehicle]:
        return [vehicle for vehicle in self._data.values() if vehicle.user_id == user_id]
