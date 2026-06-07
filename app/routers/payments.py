from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.database import get_db
from app.models.payment import Payment, PaymentStatus, PaymentType
from app.schemas.payment import PaymentCreate, PaymentPatch, PaymentOut

router = APIRouter(prefix="/payments", tags=["Платежи"])


@router.get("/", response_model=List[PaymentOut])
def list_payments(
    contract_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(Payment)
    if contract_id: q = q.filter(Payment.contract_id == contract_id)
    if status:      q = q.filter(Payment.status == status)
    if period_month:q = q.filter(Payment.period_month == period_month)
    if period_year: q = q.filter(Payment.period_year == period_year)
    return q.order_by(Payment.created_at.desc()).all()


@router.get("/schedule/{contract_id}", response_model=List[PaymentOut])
def get_schedule(contract_id: int, db: Session = Depends(get_db)):
    """План платежей по договору. Автоматически помечает просроченные как долг."""
    from datetime import datetime
    now = datetime.utcnow()

    # Обновляем просроченные pending → debt
    overdue = db.query(Payment).filter(
        Payment.contract_id == contract_id,
        Payment.status == PaymentStatus.pending,
        Payment.payment_type == "rent",
    ).all()

    changed = False
    for p in overdue:
        if p.period_year is None or p.period_month is None:
            continue
        if p.period_year < now.year or (p.period_year == now.year and p.period_month < now.month):
            p.status = PaymentStatus.debt
            changed = True

    if changed:
        db.commit()

    return db.query(Payment).filter(
        Payment.contract_id == contract_id
    ).order_by(Payment.period_year, Payment.period_month).all()


@router.get("/debts")
def get_debts(db: Session = Depends(get_db)):
    """Сводка задолженностей по всем договорам"""
    rows = db.query(
        Payment.contract_id,
        func.sum(Payment.amount_due - Payment.amount_paid).label("debt")
    ).filter(
        Payment.status.in_([PaymentStatus.debt, PaymentStatus.partial])
    ).group_by(Payment.contract_id).all()
    return [{"contract_id": r.contract_id, "debt": round(r.debt, 2)} for r in rows]


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(data: PaymentCreate, db: Session = Depends(get_db)):
    """Создать начисление."""
    payment = Payment(**data.model_dump())
    payment.status = _calc_status(data.amount_due, data.amount_paid)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentOut)
def register_payment(payment_id: int, data: PaymentPatch, db: Session = Depends(get_db)):
    """Зафиксировать оплату по начислению."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    payment.amount_paid  = data.amount_paid
    payment.payment_date = data.payment_date
    payment.comment      = data.comment or payment.comment
    payment.status       = _calc_status(payment.amount_due, data.amount_paid)
    db.commit()
    db.refresh(payment)
    return payment


def _calc_status(due: float, paid: float) -> PaymentStatus:
    if paid <= 0:    return PaymentStatus.debt
    if paid >= due:  return PaymentStatus.paid
    return PaymentStatus.partial
