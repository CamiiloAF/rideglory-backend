from abc import ABC, abstractmethod

from services.vehicles.app.domain.entities.vehicle import (
    CreateVehicle,
    UpdateVehicle,
    Vehicle,
)


class VehicleRepository(ABC):
    """Repository interface for vehicle operations."""

    @abstractmethod
    def get_vehicles_by_user_id(self, user_id: str) -> list[Vehicle]:
        raise NotImplementedError

    @abstractmethod
    def create_vehicle(self, vehicle: CreateVehicle) -> Vehicle:
        raise NotImplementedError

    @abstractmethod
    def update_vehicle(self, vehicle_id: str, vehicle: UpdateVehicle) -> Vehicle:
        raise NotImplementedError

    @abstractmethod
    def delete_vehicle(self, vehicle_id: str) -> None:
        raise NotImplementedError
