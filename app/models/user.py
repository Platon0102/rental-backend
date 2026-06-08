import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class UserRole(str, enum.Enum):
    superadmin  = "superadmin"
    bc_admin    = "bc_admin"
    manager     = "manager"
    accountant  = "accountant"


class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True, index=True)
    email               = Column(String(100), unique=True, index=True, nullable=False)
    full_name           = Column(String(200), nullable=True)
    hashed_password     = Column(String(300), nullable=False)
    is_active           = Column(Boolean, default=True)
    role                = Column(Enum(UserRole), default=UserRole.manager, nullable=False)
    business_center_id  = Column(Integer, ForeignKey("business_centers.id"), nullable=True)
    created_at          = Column(DateTime, server_default=func.now())

    business_center = relationship("BusinessCenter", back_populates="users")
