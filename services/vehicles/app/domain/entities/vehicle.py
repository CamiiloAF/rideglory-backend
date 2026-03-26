from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class VehicleBase(BaseModel):
    """Base model for vehicle entities."""

    name: str
    brand: str
    model: str
    year: int
    current_mileage: int
    license_plate: str
    vin: Optional[str] = None
    purchase_date: Optional[date] = None
    image_url: Optional[str] = None
    is_main_vehicle: bool = False
    is_archived: bool = False


class CreateVehicle(VehicleBase):
    """Model for creating a vehicle."""


class UpdateVehicle(VehicleBase):
    """Model for updating a vehicle."""


class Vehicle(VehicleBase):
    """Vehicle with persistence metadata; allows construction from ORM objects (from_attributes)."""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
