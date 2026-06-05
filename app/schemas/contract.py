from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.contract import ContractStatus


class ContractCreate(BaseModel):
    number: str
    room_id: int
    tenant_id: int
    start_date: datetime
    end_date: datetime
    monthly_rent: float
    deposit: Optional[float] = None
    payment_day: int = 10


class ContractTerminate(BaseModel):
    terminated_at: datetime
    termination_reason: Optional[str] = None
    termination_initiator: Optional[str] = None  # "tenant"|"landlord"|"agreement"
    deposit_action: str = "return"               # "return"|"hold"|"partial"
    penalty: float = 0


class ContractOut(BaseModel):
    id: int
    number: str
    room_id: int
    tenant_id: int
    status: ContractStatus
    start_date: datetime
    end_date: datetime
    monthly_rent: float
    deposit: Optional[float] = None
    payment_day: int
    file_name: Optional[str] = None
    terminated_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}
