from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.room import RoomStatus, RoomType


class RoomBase(BaseModel):
    floor: int
    name: str
    area: float
    room_type: RoomType = RoomType.office
    base_rate: Optional[float] = None
    description: Optional[str] = None


class RoomCreate(RoomBase):
    status: RoomStatus = RoomStatus.free


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    area: Optional[float] = None
    room_type: Optional[RoomType] = None
    base_rate: Optional[float] = None
    description: Optional[str] = None
    repair_start: Optional[datetime] = None
    repair_end: Optional[datetime] = None


class RoomStatusChange(BaseModel):
    new_status: RoomStatus
    reason: Optional[str] = None
    repair_start: Optional[datetime] = None
    repair_end: Optional[datetime] = None


class RoomOut(RoomBase):
    id: int
    status: RoomStatus
    repair_start: Optional[datetime] = None
    repair_end: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
