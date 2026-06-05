from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class UtilityType(str, enum.Enum):
    electricity = "electricity"
    water_cold  = "water_cold"
    water_hot   = "water_hot"
    heat        = "heat"
    internet    = "internet"
    other       = "other"


class UtilityReading(Base):
    """Показания счётчиков по помещению за месяц"""
    __tablename__ = "utility_readings"

    id          = Column(Integer, primary_key=True, index=True)
    room_id     = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    utility_type= Column(Enum(UtilityType), nullable=False)
    meter_number= Column(String(50), nullable=True)
    period_month= Column(Integer, nullable=False)
    period_year = Column(Integer, nullable=False)
    prev_reading= Column(Float, nullable=True)
    curr_reading= Column(Float, nullable=True)
    consumption = Column(Float, nullable=True)   # расход = curr - prev
    tariff      = Column(Float, nullable=True)   # сом/ед
    amount      = Column(Float, nullable=True)   # итого = consumption * tariff
    is_fixed    = Column(Boolean, default=False) # фиксированная плата
    fixed_amount= Column(Float, nullable=True)
    created_at  = Column(DateTime, server_default=func.now())


class UtilityBill(Base):
    """Счёт за коммунальные услуги по договору за месяц"""
    __tablename__ = "utility_bills"

    id           = Column(Integer, primary_key=True, index=True)
    contract_id  = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    period_month = Column(Integer, nullable=False)
    period_year  = Column(Integer, nullable=False)
    electricity  = Column(Float, default=0)
    water_cold   = Column(Float, default=0)
    water_hot    = Column(Float, default=0)
    heat         = Column(Float, default=0)
    internet     = Column(Float, default=0)
    other        = Column(Float, default=0)
    total        = Column(Float, default=0)
    is_sent      = Column(Boolean, default=False)
    created_at   = Column(DateTime, server_default=func.now())

    contract = relationship("Contract", back_populates="utility_bills")
