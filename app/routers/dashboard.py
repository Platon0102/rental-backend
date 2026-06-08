from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app.models.room import Room, RoomStatus
from app.models.contract import Contract, ContractStatus
from app.models.payment import Payment, PaymentStatus
from app.models.user import User, UserRole
from app.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Дашборд"])


def _bc_id(current_user: User):
    return None if current_user.role == UserRole.superadmin else current_user.business_center_id


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bc_id = _bc_id(current_user)

    def room_q():
        q = db.query(func.count(Room.id))
        if bc_id:
            q = q.filter(Room.business_center_id == bc_id)
        return q

    total_rooms   = room_q().scalar()
    occupied      = room_q().filter(Room.status == RoomStatus.occupied).scalar()
    free          = room_q().filter(Room.status == RoomStatus.free).scalar()
    reserved      = room_q().filter(Room.status == RoomStatus.reserved).scalar()
    repair        = room_q().filter(Room.status == RoomStatus.repair).scalar()
    occupancy_pct = round(occupied / total_rooms * 100, 1) if total_rooms else 0

    debt_q = db.query(func.sum(Payment.amount_due - Payment.amount_paid)).filter(
        Payment.status.in_([PaymentStatus.debt, PaymentStatus.partial])
    )
    if bc_id:
        debt_q = debt_q.join(Contract).join(Room).filter(Room.business_center_id == bc_id)
    debt_total = debt_q.scalar() or 0

    now = datetime.utcnow()
    exp_q = db.query(func.count(Contract.id)).filter(
        Contract.end_date <= now + timedelta(days=30),
        Contract.status.in_([ContractStatus.active, ContractStatus.expiring])
    )
    if bc_id:
        exp_q = exp_q.join(Room).filter(Room.business_center_id == bc_id)
    expiring_30 = exp_q.scalar()

    return {
        "rooms": {"total": total_rooms, "occupied": occupied, "free": free, "reserved": reserved, "repair": repair, "occupancy_pct": occupancy_pct},
        "finance": {"debt_total": round(debt_total, 2)},
        "contracts": {"expiring_30_days": expiring_30},
    }


@router.get("/expiring-contracts")
def expiring_contracts(days: int = 90, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bc_id = _bc_id(current_user)
    deadline = datetime.utcnow() + timedelta(days=days)
    q = db.query(Contract).filter(Contract.end_date <= deadline, Contract.status.in_([ContractStatus.active, ContractStatus.expiring]))
    if bc_id:
        q = q.join(Room).filter(Room.business_center_id == bc_id)
    return q.order_by(Contract.end_date).all()


@router.get("/occupancy-by-floor")
def occupancy_by_floor(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bc_id = _bc_id(current_user)
    q = db.query(Room.floor).distinct().order_by(Room.floor)
    if bc_id:
        q = q.filter(Room.business_center_id == bc_id)
    floors = q.all()
    result = []
    for (floor,) in floors:
        base = db.query(func.count(Room.id)).filter(Room.floor == floor)
        if bc_id:
            base = base.filter(Room.business_center_id == bc_id)
        total    = base.scalar()
        occupied = base.filter(Room.status == RoomStatus.occupied).scalar()
        result.append({"floor": floor, "total": total, "occupied": occupied, "pct": round(occupied / total * 100, 1) if total else 0})
    return result


@router.get("/revenue-by-month")
def revenue_by_month(year: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    bc_id = _bc_id(current_user)
    if not year:
        year = datetime.utcnow().year
    q = db.query(Payment.period_month, func.sum(Payment.amount_paid).label("paid"), func.sum(Payment.amount_due).label("due")).filter(Payment.period_year == year)
    if bc_id:
        q = q.join(Contract).join(Room).filter(Room.business_center_id == bc_id)
    rows = q.group_by(Payment.period_month).order_by(Payment.period_month).all()
    return [{"month": r.period_month, "paid": round(r.paid or 0, 2), "due": round(r.due or 0, 2)} for r in rows]
