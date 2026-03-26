import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from services.vehicles.app.domain.entities.vehicle import (
    CreateVehicle,
    UpdateVehicle,
    Vehicle,
)
from services.vehicles.app.domain.repositories.vehicle_repository import (
    VehicleRepository,
)
from services.vehicles.app.infrastructure.models.vehicle import VehicleModel


class VehicleRepositoryImpl(VehicleRepository):
    """Implementation of the vehicle repository."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def _get_existing_vehicle(self, vehicle_id: str) -> VehicleModel:
        existing_vehicle = (
            self._db.query(VehicleModel).filter(VehicleModel.id == vehicle_id).first()
        )

        if not existing_vehicle:
            raise ValueError(f"Vehicle with id {vehicle_id} not found")

        return existing_vehicle

    def create_vehicle(self, vehicle: CreateVehicle) -> Vehicle:
        new_vehicle = VehicleModel(
            id=str(uuid.uuid4()),
            name=vehicle.name,
            brand=vehicle.brand,
            model=vehicle.model,
            year=vehicle.year,
            current_mileage=vehicle.current_mileage,
            license_plate=vehicle.license_plate,
            vin=vehicle.vin,
            purchase_date=vehicle.purchase_date,
            image_url=vehicle.image_url,
            is_main_vehicle=vehicle.is_main_vehicle,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        self._db.add(new_vehicle)
        self._db.commit()
        self._db.refresh(new_vehicle)

        return new_vehicle

    def update_vehicle(self, vehicle_id: str, vehicle: UpdateVehicle) -> Vehicle:
        existing_vehicle = self._get_existing_vehicle(vehicle_id)

        for key, value in vehicle.model_dump().items():
            setattr(existing_vehicle, key, value)

        self._db.commit()
        self._db.refresh(existing_vehicle)

        return existing_vehicle

    def get_vehicles_by_user_id(self, user_id: str) -> list[Vehicle]:
        return (
            self._db.query(VehicleModel)
            # .filter(VehicleModel.user_id == user_id)
            .all()
        )

    def delete_vehicle(self, vehicle_id: str) -> None:
        existing_vehicle = (
            self._db.query(VehicleModel).filter(VehicleModel.id == vehicle_id).first()
        )

        if not existing_vehicle:
            raise ValueError(f"Vehicle with id {vehicle_id} not found")

        self._db.delete(existing_vehicle)
        self._db.commit()
