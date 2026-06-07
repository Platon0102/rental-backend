from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.room import Room, RoomStatus, RoomStatusHistory
from app.schemas.room import RoomCreate, RoomUpdate, RoomOut, RoomStatusChange

router = APIRouter(prefix="/rooms", tags=["Помещения"])


@router.get("/", response_model=List[RoomOut])
def list_rooms(
    floor: Optional[int] = None,
    status: Optional[RoomStatus] = None,
    db: Session = Depends(get_db)
):
    """Список всех помещений с фильтрацией по этажу и статусу"""
    q = db.query(Room)
    if floor:
        q = q.filter(Room.floor == floor)
    if status:
        q = q.filter(Room.status == status)
    return q.order_by(Room.floor, Room.name).all()


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    return room


@router.post("/", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(data: RoomCreate, db: Session = Depends(get_db)):
    """Создать новое помещение"""
    room = Room(**data.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.patch("/{room_id}", response_model=RoomOut)
def update_room(room_id: int, data: RoomUpdate, db: Session = Depends(get_db)):
    """Редактировать характеристики помещения"""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room


@router.post("/{room_id}/status", response_model=RoomOut)
def change_room_status(
    room_id: int,
    data: RoomStatusChange,
    db: Session = Depends(get_db)
):
    """
    Сменить статус помещения.
    Допустимые переходы:
      free      → repair, reserved
      reserved  → free, repair
      repair    → free, reserved
      occupied  → repair (только после расторжения договора)
    """
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Помещение не найдено")

    # Проверка: занятое помещение нельзя перевести в ремонт без расторжения
    if room.status == RoomStatus.occupied and data.new_status == RoomStatus.repair:
        from app.models.contract import Contract, ContractStatus
        active = db.query(Contract).filter(
            Contract.room_id == room_id,
            Contract.status == ContractStatus.active
        ).first()
        if active:
            raise HTTPException(
                status_code=400,
                detail="Сначала расторгните активный договор аренды"
            )

    # Сохранить историю смены статуса
    history = RoomStatusHistory(
        room_id=room_id,
        old_status=room.status,
        new_status=data.new_status,
        reason=data.reason
    )
    db.add(history)

    # Обновить поля
    room.status = data.new_status
    if data.new_status == RoomStatus.repair:
        room.repair_start = data.repair_start
        room.repair_end   = data.repair_end
    elif data.new_status == RoomStatus.free:
        room.repair_start = None
        room.repair_end   = None

    db.commit()
    db.refresh(room)
    return room


@router.get("/{room_id}/history")
def room_status_history(room_id: int, db: Session = Depends(get_db)):
    """История смен статуса помещения"""
    history = db.query(RoomStatusHistory).filter(
        RoomStatusHistory.room_id == room_id
    ).order_by(RoomStatusHistory.changed_at.desc()).all()
    return history


@router.get("/{room_id}/full-history")
def room_full_history(room_id: int, db: Session = Depends(get_db)):
    """
    Полная история помещения:
    - все договоры (с арендатором и платежами)
    - история смен статуса
    """
    from app.models.contract import Contract
    from app.models.payment import Payment
    from app.models.tenant import Tenant

    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Помещение не найдено")

    # Все договоры по помещению
    contracts = db.query(Contract).filter(
        Contract.room_id == room_id
    ).order_by(Contract.start_date.desc()).all()

    contracts_data = []
    for c in contracts:
        tenant = db.query(Tenant).filter(Tenant.id == c.tenant_id).first()
        payments = db.query(Payment).filter(
            Payment.contract_id == c.id
        ).order_by(Payment.period_year, Payment.period_month).all()

        total_due  = sum(p.amount_due for p in payments)
        total_paid = sum(p.amount_paid for p in payments)

        contracts_data.append({
            "id":           c.id,
            "number":       c.number,
            "status":       c.status,
            "start_date":   c.start_date.isoformat() if c.start_date else None,
            "end_date":     c.end_date.isoformat() if c.end_date else None,
            "terminated_at": c.terminated_at.isoformat() if c.terminated_at else None,
            "monthly_rent": c.monthly_rent,
            "deposit":      c.deposit,
            "termination_reason": c.termination_reason,
            "tenant": {
                "id":             tenant.id if tenant else None,
                "name":           tenant.name if tenant else "—",
                "inn":            tenant.inn if tenant else None,
                "phone":          tenant.phone if tenant else None,
                "contact_person": tenant.contact_person if tenant else None,
            },
            "payments_summary": {
                "total_months": len(payments),
                "paid_months":  sum(1 for p in payments if p.status == "paid"),
                "total_due":    total_due,
                "total_paid":   total_paid,
                "debt":         max(0, total_due - total_paid),
            },
            "payments": [
                {
                    "id":           p.id,
                    "period_month": p.period_month,
                    "period_year":  p.period_year,
                    "amount_due":   p.amount_due,
                    "amount_paid":  p.amount_paid,
                    "status":       p.status,
                    "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                }
                for p in payments
            ],
        })

    # История смен статуса
    status_history = db.query(RoomStatusHistory).filter(
        RoomStatusHistory.room_id == room_id
    ).order_by(RoomStatusHistory.changed_at.desc()).all()

    return {
        "room": {
            "id":        room.id,
            "name":      room.name,
            "floor":     room.floor,
            "area":      room.area,
            "base_rate": room.base_rate,
            "status":    room.status,
        },
        "contracts": contracts_data,
        "status_history": [
            {
                "old_status": h.old_status,
                "new_status": h.new_status,
                "reason":     h.reason,
                "changed_at": h.changed_at.isoformat() if h.changed_at else None,
            }
            for h in status_history
        ],
    }


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    db.delete(room)
    db.commit()
