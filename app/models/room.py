from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class RoomStatus(str, enum.Enum):
    free     = "free"
    occupied = "occupied"
    reserved = "reserved"
    repair   = "repair"


class RoomType(str, enum.Enum):
    office      = "office"
    open_space  = "open_space"
    meeting     = "meeting"
    warehouse   = "warehouse"
    other       = "other"


class Room(Base):
    __tablename__ = "rooms"

    id          = Column(Integer, primary_key=True, index=True)
    floor       = Column(Integer, nullable=False)
    name        = Column(String(100), nullable=False)
    area        = Column(Float, nullable=False)
    room_type   = Column(Enum(RoomType), default=RoomType.office)
    status      = Column(Enum(RoomStatus), default=RoomStatus.free)
    base_rate   = Column(Float, nullable=True)          # сом/мес
    description = Column(Text, nullable=True)
    repair_start= Column(DateTime, nullable=True)
    repair_end  = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, server_default=func.now())
    updated_at  = Column(DateTime, onupdate=func.now())

    contracts       = relationship("Contract", back_populates="room")
    status_history  = relationship("RoomStatusHistory", back_populates="room",
                                   order_by="RoomStatusHistory.changed_at.desc()")


class RoomStatusHistory(Base):
    __tablename__ = "room_status_history"

    id          = Column(Integer, primary_key=True, index=True)
    room_id     = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    old_status  = Column(Enum(RoomStatus), nullable=True)
    new_status  = Column(Enum(RoomStatus), nullable=False)
    reason      = Column(String(300), nullable=True)
    changed_at  = Column(DateTime, server_default=func.now())
    changed_by  = Column(Integer, ForeignKey("users.id"), nullable=True)

    room = relationship("Room", back_populates="status_history")
