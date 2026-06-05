from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class PaymentType(str, enum.Enum):
    rent      = "rent"
    utilities = "utilities"
    deposit   = "deposit"
    penalty   = "penalty"
    other     = "other"


class PaymentStatus(str, enum.Enum):
    paid    = "paid"
    partial = "partial"
    debt    = "debt"
    pending = "pending"


class Payment(Base):
    __tablename__ = "payments"

    id           = Column(Integer, primary_key=True, index=True)
    contract_id  = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    payment_type = Column(Enum(PaymentType), default=PaymentType.rent)
    period_month = Column(Integer, nullable=True)   # месяц (1–12)
    period_year  = Column(Integer, nullable=True)   # год
    amount_due   = Column(Float, nullable=False)    # начислено
    amount_paid  = Column(Float, default=0)         # оплачено
    payment_date = Column(DateTime, nullable=True)  # дата поступления
    status       = Column(Enum(PaymentStatus), default=PaymentStatus.pending)
    comment      = Column(String(300), nullable=True)
    created_at   = Column(DateTime, server_default=func.now())

    contract = relationship("Contract", back_populates="payments")

    @property
    def debt(self):
        return max(0, self.amount_due - self.amount_paid)
