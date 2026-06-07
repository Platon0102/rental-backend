from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from app.database import get_db
from app.config import settings
from app.telegram import send_message, get_chat_id_from_updates

router = APIRouter(prefix="/notifications", tags=["Уведомления"])

# Храним chat_id в памяти (в продакшене — в БД или .env)
_chat_id_store: dict[str, str] = {}


class TelegramSettings(BaseModel):
    chat_id: str


@router.get("/telegram/status")
async def telegram_status():
    """Статус подключения Telegram-бота."""
    chat_id = _chat_id_store.get("chat_id") or settings.TELEGRAM_CHAT_ID
    return {
        "token_set": bool(settings.TELEGRAM_TOKEN),
        "chat_id": chat_id,
        "connected": bool(chat_id),
    }


@router.post("/telegram/detect-chat")
async def detect_chat_id():
    """
    Автоматически определить chat_id из последних сообщений боту.
    Пользователь должен написать /start боту перед вызовом этого endpoint.
    """
    chat_id = await get_chat_id_from_updates()
    if not chat_id:
        raise HTTPException(
            status_code=404,
            detail="Сообщений не найдено. Напишите /start боту и повторите."
        )
    _chat_id_store["chat_id"] = chat_id
    return {"chat_id": chat_id, "ok": True}


@router.post("/telegram/save-chat")
async def save_chat_id(data: TelegramSettings):
    """Сохранить chat_id вручную."""
    _chat_id_store["chat_id"] = data.chat_id
    return {"ok": True, "chat_id": data.chat_id}


@router.post("/telegram/test")
async def send_test(db: Session = Depends(get_db)):
    """Отправить тестовое сообщение."""
    chat_id = _chat_id_store.get("chat_id") or settings.TELEGRAM_CHAT_ID
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id не настроен")

    ok = await send_message(chat_id,
        "✅ <b>БЦ «Золотой»</b>\n\nТестовое сообщение — бот подключён успешно!"
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Ошибка отправки. Проверьте токен и chat_id.")
    return {"ok": True}


@router.post("/telegram/send-alerts")
async def send_alerts(db: Session = Depends(get_db)):
    """Отправить уведомления о просроченных платежах и истекающих договорах."""
    from app.models.payment import Payment, PaymentStatus
    from app.models.contract import Contract, ContractStatus
    from app.models.tenant import Tenant
    from app.models.room import Room

    chat_id = _chat_id_store.get("chat_id") or settings.TELEGRAM_CHAT_ID
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id не настроен")

    now = datetime.utcnow()
    messages = []

    # 1. Просроченные платежи (debt)
    debts = db.query(Payment).filter(
        Payment.status == PaymentStatus.debt
    ).all()

    # 2. Pending платежи за прошедшие месяцы
    overdue_pending = db.query(Payment).filter(
        Payment.status == PaymentStatus.pending
    ).all()
    overdue_pending = [
        p for p in overdue_pending
        if p.period_year and p.period_month and (
            p.period_year < now.year or
            (p.period_year == now.year and p.period_month < now.month)
        )
    ]

    all_overdue = debts + overdue_pending

    if all_overdue:
        lines = ["🔴 <b>Просроченные платежи:</b>\n"]
        for p in all_overdue[:10]:
            contract = db.query(Contract).filter(Contract.id == p.contract_id).first()
            tenant = db.query(Tenant).filter(Tenant.id == contract.tenant_id).first() if contract else None
            room = db.query(Room).filter(Room.id == contract.room_id).first() if contract else None
            debt = p.amount_due - p.amount_paid
            lines.append(
                f"• {tenant.name if tenant else '?'} ({room.name if room else '?'}) — "
                f"{int(debt):,} сом".replace(",", " ")
            )
        messages.append("\n".join(lines))

    # 3. Истекающие договоры (30 дней)
    deadline = now + timedelta(days=30)
    expiring = db.query(Contract).filter(
        Contract.status.in_([ContractStatus.active, ContractStatus.expiring]),
        Contract.end_date <= deadline,
        Contract.end_date >= now,
    ).all()

    if expiring:
        lines = ["\n⚠️ <b>Договоры истекают (30 дней):</b>\n"]
        for c in expiring:
            tenant = db.query(Tenant).filter(Tenant.id == c.tenant_id).first()
            room = db.query(Room).filter(Room.id == c.room_id).first()
            days = (c.end_date - now).days
            lines.append(
                f"• {tenant.name if tenant else '?'} ({room.name if room else '?'}) — "
                f"через {days} дн. ({c.end_date.strftime('%d.%m.%Y')})"
            )
        messages.append("\n".join(lines))

    if not messages:
        text = "✅ <b>БЦ «Золотой»</b>\n\nВсё в порядке — просроченных платежей и истекающих договоров нет."
    else:
        text = f"📊 <b>БЦ «Золотой»</b> — Отчёт {now.strftime('%d.%m.%Y %H:%M')}\n\n" + "\n".join(messages)

    ok = await send_message(chat_id, text)
    if not ok:
        raise HTTPException(status_code=500, detail="Ошибка отправки сообщения")

    return {
        "ok": True,
        "sent": True,
        "overdue_count": len(all_overdue),
        "expiring_count": len(expiring),
    }
