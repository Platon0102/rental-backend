from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class BusinessCenter(Base):
    __tablename__ = "business_centers"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(200), nullable=False)
    address      = Column(String(300), nullable=True)
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, server_default=func.now())

    users    = relationship("User", back_populates="business_center")
    rooms    = relationship("Room", back_populates="business_center")
    tenants  = relationship("Tenant", back_populates="business_center")
