from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class ContractStatus(str, enum.Enum):
    active     = "active"
    expiring   = "expiring"
    expired    = "expired"
    reserved   = "reserved"
    terminated = "terminated"


class Contract(Base):
    __tablename__ = "contracts"

    id              = Column(Integer, primary_key=True, index=True)
    number          = Column(String(50), nullable=False, unique=True, index=True)
    room_id         = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    tenant_id       = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    status          = Column(Enum(ContractStatus), default=ContractStatus.active)

    start_date      = Column(DateTime, nullable=False)
    end_date        = Column(DateTime, nullable=False)
    monthly_rent    = Column(Float, nullable=False)     # сом
    deposit         = Column(Float, nullable=True)
    payment_day     = Column(Integer, default=10)       # день месяца

    # Досрочное расторжение
    terminated_at   = Column(DateTime, nullable=True)
    termination_reason = Column(Text, nullable=True)
    termination_initiator = Column(String(50), nullable=True)
    penalty         = Column(Float, default=0)

    # Файл договора
    file_path       = Column(String(500), nullable=True)
    file_name       = Column(String(200), nullable=True)

    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, onupdate=func.now())

    room     = relationship("Room", back_populates="contracts")
    tenant   = relationship("Tenant", back_populates="contracts")
    payments = relationship("Payment", back_populates="contract")
    utility_bills = relationship("UtilityBill", back_populates="contract")
