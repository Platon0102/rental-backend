from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.utility import UtilityType


class UtilityReadingCreate(BaseModel):
    room_id: int
    utility_type: UtilityType
    meter_number: Optional[str] = None
    period_month: int
    period_year: int
    prev_reading: Optional[float] = None
    curr_reading: Optional[float] = None
    tariff: Optional[float] = None
    is_fixed: bool = False
    fixed_amount: Optional[float] = None


class UtilityReadingOut(UtilityReadingCreate):
    id: int
    consumption: Optional[float] = None
    amount: Optional[float] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class UtilityBillOut(BaseModel):
    id: int
    contract_id: int
    period_month: int
    period_year: int
    electricity: float
    water_cold: float
    water_hot: float
    heat: float
    internet: float
    other: float
    total: float
    is_sent: bool
    created_at: datetime
    model_config = {"from_attributes": True}
