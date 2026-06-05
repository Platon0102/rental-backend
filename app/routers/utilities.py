from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.utility import UtilityReading, UtilityBill
from app.schemas.utility import UtilityReadingCreate, UtilityReadingOut, UtilityBillOut

router = APIRouter(prefix="/utilities", tags=["Коммунальные услуги"])


@router.post("/readings/", response_model=UtilityReadingOut, status_code=201)
def add_reading(data: UtilityReadingCreate, db: Session = Depends(get_db)):
    """Ввести показания счётчика. Расход и сумма считаются автоматически."""
    reading = UtilityReading(**data.model_dump())
    if not data.is_fixed and data.curr_reading and data.prev_reading:
        reading.consumption = round(data.curr_reading - data.prev_reading, 3)
        if data.tariff:
            reading.amount = round(reading.consumption * data.tariff, 2)
    elif data.is_fixed and data.fixed_amount:
        reading.amount = data.fixed_amount
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


@router.get("/readings/", response_model=List[UtilityReadingOut])
def list_readings(
    room_id: Optional[int] = None,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(UtilityReading)
    if room_id:      q = q.filter(UtilityReading.room_id == room_id)
    if period_month: q = q.filter(UtilityReading.period_month == period_month)
    if period_year:  q = q.filter(UtilityReading.period_year == period_year)
    return q.all()


@router.post("/bills/generate")
def generate_bills(
    period_month: int,
    period_year: int,
    db: Session = Depends(get_db)
):
    """
    Собрать показания за период → создать счета по всем активным договорам.
    Возвращает список созданных счетов.
    """
    from app.models.contract import Contract, ContractStatus
    from app.models.utility import UtilityType

    contracts = db.query(Contract).filter(
        Contract.status.in_([ContractStatus.active, ContractStatus.expiring])
    ).all()

    bills = []
    for contract in contracts:
        readings = db.query(UtilityReading).filter(
            UtilityReading.room_id == contract.room_id,
            UtilityReading.period_month == period_month,
            UtilityReading.period_year == period_year
        ).all()

        amounts = {r.utility_type: (r.amount or 0) for r in readings}
        total = sum(amounts.values())

        bill = UtilityBill(
            contract_id  = contract.id,
            period_month = period_month,
            period_year  = period_year,
            electricity  = amounts.get(UtilityType.electricity, 0),
            water_cold   = amounts.get(UtilityType.water_cold, 0),
            water_hot    = amounts.get(UtilityType.water_hot, 0),
            heat         = amounts.get(UtilityType.heat, 0),
            internet     = amounts.get(UtilityType.internet, 0),
            other        = amounts.get(UtilityType.other, 0),
            total        = round(total, 2),
        )
        db.add(bill)
        bills.append(bill)

    db.commit()
    return {"generated": len(bills), "period": f"{period_month}/{period_year}"}


@router.get("/bills/", response_model=List[UtilityBillOut])
def list_bills(
    contract_id: Optional[int] = None,
    period_month: Optional[int] = None,
    period_year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(UtilityBill)
    if contract_id:  q = q.filter(UtilityBill.contract_id == contract_id)
    if period_month: q = q.filter(UtilityBill.period_month == period_month)
    if period_year:  q = q.filter(UtilityBill.period_year == period_year)
    return q.all()


@router.patch("/bills/{bill_id}/send")
def mark_bill_sent(bill_id: int, db: Session = Depends(get_db)):
    """Отметить счёт как отправленный арендатору."""
    bill = db.query(UtilityBill).filter(UtilityBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Счёт не найден")
    bill.is_sent = True
    db.commit()
    return {"ok": True}
