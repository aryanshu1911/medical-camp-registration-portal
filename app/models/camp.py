from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Camp(Base):
    __tablename__ = "camps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    date = Column(String(20), nullable=False)
    location = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    available_slots = Column(Integer, nullable=False)

    status = Column(
        String(20),
        nullable=False,
        default="scheduled"
    )

    registrations = relationship(
        "Registration",
        back_populates="camp"
    )