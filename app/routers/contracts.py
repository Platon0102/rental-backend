from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import shutil, os
from app.database import get_db
from app.models.contract import Contract, ContractStatus
from app.models.room import Room, RoomStatus
from app.models.payment import Payment, PaymentType, PaymentStatus
from app.schemas.contract import ContractCreate, ContractOut, ContractTerminate
from app.config import settings


def _generate_payment_schedule(db: Session, contract: Contract):
    """Генерирует план платежей (по одному на каждый месяц договора)."""
    year = contract.start_date.year
    month = contract.start_date.month
    end_year = contract.end_date.year
    end_month = contract.end_date.month

    while (year, month) <= (end_year, end_month):
        payment = Payment(
            contract_id=contract.id,
            payment_type=PaymentType.rent,
            period_month=month,
            period_year=year,
            amount_due=contract.monthly_rent,
            amount_paid=0,
            status=PaymentStatus.pending,
        )
        db.add(payment)
        # следующий месяц
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    db.commit()

router = APIRouter(prefix="/contracts", tags=["Договоры"])


def _get_or_404(db, contract_id):
    c = db.query(Contract).filter(Contract.id == contract_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Договор не найден")
    return c


@router.get("/", response_model=List[ContractOut])
def list_contracts(
    status: Optional[ContractStatus] = None,
    tenant_id: Optional[int] = None,
    room_id: Optional[int] = None,
    expiring_days: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Список договоров.
    expiring_days — договоры, истекающие через N дней (для уведомлений).
    """
    q = db.query(Contract)
    if status:
        q = q.filter(Contract.status == status)
    if tenant_id:
        q = q.filter(Contract.tenant_id == tenant_id)
    if room_id:
        q = q.filter(Contract.room_id == room_id)
    if expiring_days:
        deadline = datetime.utcnow().replace(
            hour=0, minute=0, second=0
        )
        from datetime import timedelta
        target = deadline + timedelta(days=expiring_days)
        q = q.filter(
            Contract.end_date <= target,
            Contract.status.in_([ContractStatus.active, ContractStatus.expiring])
        )
    return q.order_by(Contract.end_date).all()


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, contract_id)


@router.post("/", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(data: ContractCreate, db: Session = Depends(get_db)):
    """Создать договор. Автоматически переводит помещение в статус Занято."""
    room = db.query(Room).filter(Room.id == data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Помещение не найдено")
    if room.status == RoomStatus.occupied:
        raise HTTPException(status_code=400, detail="Помещение уже занято")

    contract = Contract(**data.model_dump())
    db.add(contract)
    room.status = RoomStatus.occupied
    db.commit()
    db.refresh(contract)

    # Автоматически генерируем план ежемесячных платежей
    _generate_payment_schedule(db, contract)

    return contract


@router.post("/{contract_id}/upload", response_model=ContractOut)
async def upload_contract_file(
    contract_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Прикрепить скан договора (PDF/JPG/PNG)."""
    contract = _get_or_404(db, contract_id)
    allowed = {".pdf", ".jpg", ".jpeg", ".png"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Допустимые форматы: PDF, JPG, PNG")

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Файл больше {settings.MAX_FILE_SIZE_MB} МБ")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    save_name = f"contract_{contract_id}_{file.filename}"
    save_path = os.path.join(settings.UPLOAD_DIR, save_name)
    with open(save_path, "wb") as f:
        f.write(content)

    contract.file_path = save_path
    contract.file_name = file.filename
    db.commit()
    db.refresh(contract)
    return contract


@router.post("/{contract_id}/terminate", response_model=ContractOut)
def terminate_contract(
    contract_id: int,
    data: ContractTerminate,
    db: Session = Depends(get_db)
):
    """
    Досрочное расторжение договора.
    Автоматически переводит помещение в статус Свободно.
    """
    contract = _get_or_404(db, contract_id)
    if contract.status == ContractStatus.terminated:
        raise HTTPException(status_code=400, detail="Договор уже расторгнут")

    contract.status                 = ContractStatus.terminated
    contract.terminated_at          = data.terminated_at
    contract.termination_reason     = data.termination_reason
    contract.termination_initiator  = data.termination_initiator
    contract.penalty                = data.penalty

    room = db.query(Room).filter(Room.id == contract.room_id).first()
    if room:
        room.status = RoomStatus.free

    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    contract = _get_or_404(db, contract_id)
    db.delete(contract)
    db.commit()
