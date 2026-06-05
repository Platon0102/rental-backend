from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.tenant import TenantType


class TenantBase(BaseModel):
    name: str
    tenant_type: TenantType = TenantType.ooo
    inn: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    tenant_type: Optional[TenantType] = None
    inn: Optional[str] = None
    contact_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class TenantOut(TenantBase):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}
