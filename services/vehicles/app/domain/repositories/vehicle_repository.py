from abc import ABC, abstractmethod

from services.vehicles.app.domain.entities.vehicle import Vehicle


class VehicleRepository(ABC):
    @abstractmethod
    def save(self, vehicle: Vehicle) -> Vehicle:
        raise NotImplementedError

    @abstractmethod
    def getVehiclesByUserId(self, user_id: str) -> list[Vehicle]:
        raise NotImplementedError
