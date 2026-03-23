from services.vehicles.app.domain.entities.vehicle import Vehicle
from services.vehicles.app.domain.repositories.vehicle_repository import VehicleRepository


class GetVehiclesByUserIdUseCase:
    def __init__(self, vehicle_repository: VehicleRepository) -> None:
        self._vehicle_repository = vehicle_repository

    def execute(self, user_id: str) -> list[Vehicle]:
        return self._vehicle_repository.getVehiclesByUserId(user_id)