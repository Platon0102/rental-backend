from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app.models.room import Room, RoomStatus
from app.models.contract import Contract, ContractStatus
from app.models.payment import Payment, PaymentStatus

router = APIRouter(prefix="/dashboard", tags=["Дашборд"])


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Общая статистика для главного экрана."""
    total_rooms    = db.query(func.count(Room.id)).scalar()
    occupied       = db.query(func.count(Room.id)).filter(Room.status == RoomStatus.occupied).scalar()
    free           = db.query(func.count(Room.id)).filter(Room.status == RoomStatus.free).scalar()
    reserved       = db.query(func.count(Room.id)).filter(Room.status == RoomStatus.reserved).scalar()
    repair         = db.query(func.count(Room.id)).filter(Room.status == RoomStatus.repair).scalar()
    occupancy_pct  = round(occupied / total_rooms * 100, 1) if total_rooms else 0

    # Задолженность
    debt_total = db.query(
        func.sum(Payment.amount_due - Payment.amount_paid)
    ).filter(Payment.status.in_([PaymentStatus.debt, PaymentStatus.partial])).scalar() or 0

    # Договоры истекают через 30 / 60 / 90 дней
    now = datetime.utcnow()
    expiring_30 = db.query(func.count(Contract.id)).filter(
        Contract.end_date <= now + timedelta(days=30),
        Contract.status.in_([ContractStatus.active, ContractStatus.expiring])
    ).scalar()

    return {
        "rooms": {
            "total": total_rooms,
            "occupied": occupied,
            "free": free,
            "reserved": reserved,
            "repair": repair,
            "occupancy_pct": occupancy_pct,
        },
        "finance": {
            "debt_total": round(debt_total, 2),
        },
        "contracts": {
            "expiring_30_days": expiring_30,
        }
    }


@router.get("/expiring-contracts")
def expiring_contracts(days: int = 90, db: Session = Depends(get_db)):
    """Договоры, истекающие в ближайшие N дней."""
    deadline = datetime.utcnow() + timedelta(days=days)
    contracts = db.query(Contract).filter(
        Contract.end_date <= deadline,
        Contract.status.in_([ContractStatus.active, ContractStatus.expiring])
    ).order_by(Contract.end_date).all()
    return contracts


@router.get("/occupancy-by-floor")
def occupancy_by_floor(db: Session = Depends(get_db)):
    """Заполняемость по каждому этажу."""
    floors = db.query(Room.floor).distinct().order_by(Room.floor).all()
    result = []
    for (floor,) in floors:
        total    = db.query(func.count(Room.id)).filter(Room.floor == floor).scalar()
        occupied = db.query(func.count(Room.id)).filter(
            Room.floor == floor, Room.status == RoomStatus.occupied
        ).scalar()
        result.append({
            "floor": floor,
            "total": total,
            "occupied": occupied,
            "pct": round(occupied / total * 100, 1) if total else 0
        })
    return result


@router.get("/revenue-by-month")
def revenue_by_month(year: int = None, db: Session = Depends(get_db)):
    """Поступления по месяцам."""
    if not year:
        year = datetime.utcnow().year
    rows = db.query(
        Payment.period_month,
        func.sum(Payment.amount_paid).label("paid"),
        func.sum(Payment.amount_due).label("due"),
    ).filter(
        Payment.period_year == year
    ).group_by(Payment.period_month).order_by(Payment.period_month).all()

    return [
        {"month": r.period_month, "paid": round(r.paid or 0, 2), "due": round(r.due or 0, 2)}
        for r in rows
    ]
