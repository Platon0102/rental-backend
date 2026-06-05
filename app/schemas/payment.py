from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.payment import PaymentType, PaymentStatus


class PaymentCreate(BaseModel):
    contract_id: int
    payment_type: PaymentType = PaymentType.rent
    period_month: Optional[int] = None
    period_year: Optional[int] = None
    amount_due: float
    amount_paid: float = 0
    payment_date: Optional[datetime] = None
    comment: Optional[str] = None


class PaymentPatch(BaseModel):
    amount_paid: float
    payment_date: Optional[datetime] = None
    comment: Optional[str] = None


class PaymentOut(BaseModel):
    id: int
    contract_id: int
    payment_type: PaymentType
    period_month: Optional[int] = None
    period_year: Optional[int] = None
    amount_due: float
    amount_paid: float
    status: PaymentStatus
    payment_date: Optional[datetime] = None
    comment: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}
