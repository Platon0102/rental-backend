from sqlalchemy import Column, Integer, String, DateTime, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class TenantType(str, enum.Enum):
    ooo  = "ООО"
    ao   = "АО"
    pao  = "ПАО"
    ip   = "ИП"
    other= "Другое"


class Tenant(Base):
    __tablename__ = "tenants"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(200), nullable=False, index=True)
    tenant_type  = Column(Enum(TenantType), default=TenantType.ooo)
    inn          = Column(String(20), nullable=True, unique=True)
    contact_name = Column(String(200), nullable=True)
    phone        = Column(String(30), nullable=True)
    email        = Column(String(100), nullable=True)
    address      = Column(String(300), nullable=True)
    notes        = Column(Text, nullable=True)
    created_at   = Column(DateTime, server_default=func.now())

    contracts = relationship("Contract", back_populates="tenant")
