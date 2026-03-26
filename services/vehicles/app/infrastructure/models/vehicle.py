from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from shared.infrastructure.database.database import Base


class VehicleModel(Base):
    """ORM mapping for persisted vehicle rows in the ``vehicles`` table."""

    __tablename__ = "vehicles"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    brand = Column(String)
    model = Column(String)
    year = Column(Integer)
    current_mileage = Column(Integer)
    license_plate = Column(String)
    vin = Column(String)
    purchase_date = Column(DateTime)
    image_url = Column(String)

    is_archived = Column(Boolean, default=False)
    is_main_vehicle = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

    # user_id = Column(String, ForeignKey("users.id"))
    # user = relationship("User", back_populates="vehicles")
