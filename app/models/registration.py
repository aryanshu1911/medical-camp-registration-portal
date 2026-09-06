from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    age = Column(Integer, nullable=False)
    contact_number = Column(String(15), nullable=False)

    camp_id = Column(
        Integer,
        ForeignKey("camps.id"),
        nullable=False
    )

    registered_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    camp = relationship(
        "Camp",
        back_populates="registrations"
    )