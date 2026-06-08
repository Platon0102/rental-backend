from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, ForeignKey, UniqueConstraint
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

    id                  = Column(Integer, primary_key=True, index=True)
    business_center_id  = Column(Integer, ForeignKey("business_centers.id"), nullable=False)
    name                = Column(String(200), nullable=False, index=True)
    tenant_type  = Column(Enum(TenantType), default=TenantType.ooo)
    inn          = Column(String(20), nullable=True)
    contact_name = Column(String(200), nullable=True)
    phone        = Column(String(30), nullable=True)
    email        = Column(String(100), nullable=True)
    address      = Column(String(300), nullable=True)
    notes        = Column(Text, nullable=True)
    created_at   = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('inn', 'business_center_id', name='uq_tenant_inn_per_bc'),
    )

    business_center = relationship("BusinessCenter", back_populates="tenants")
    contracts = relationship("Contract", back_populates="tenant")
