"""
Telegram-бот с командами для проверки статуса БЦ.
Запускается как фоновая задача при старте FastAPI.
"""
import asyncio
import httpx
from app.config import settings

BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}"
_offset: int = 0
_running = False


MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "📊 Статус помещений"}, {"text": "💰 Задолженности"}],
        [{"text": "📬 Уведомления"}],
    ],
    "resize_keyboard": True,
    "persistent": True,
}


async def send(chat_id: str | int, text: str, keyboard: dict | None = None):
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{BASE}/sendMessage", json=payload)


async def handle_update(update: dict):
    msg = update.get("message") or update.get("channel_post")
    if not msg:
        return

    chat_id = msg["chat"]["id"]
    text = msg.get("text", "").strip()

    if text.startswith("/start"):
        await send(chat_id,
            "👋 <b>БЦ «Золотой»</b>\n\n"
            "Выберите нужный раздел кнопками ниже 👇",
            keyboard=MAIN_KEYBOARD
        )

    elif text in ("/status", "📊 Статус помещений"):
        await cmd_status(chat_id)

    elif text in ("/debt", "💰 Задолженности"):
        await cmd_debt(chat_id)

    elif text in ("/alerts", "📬 Уведомления"):
        await cmd_alerts(chat_id)

    else:
        await send(chat_id,
            "Используйте кнопки меню 👇",
            keyboard=MAIN_KEYBOARD
        )


async def cmd_status(chat_id: str | int):
    """Свободные/занятые помещения по этажам."""
    from app.database import SessionLocal
    from app.models.room import Room, RoomStatus

    db = SessionLocal()
    try:
        rooms = db.query(Room).order_by(Room.floor, Room.name).all()
        if not rooms:
            await send(chat_id, "Помещений не найдено.")
            return

        floors: dict[int, list] = {}
        for r in rooms:
            floors.setdefault(r.floor, []).append(r)

        total = len(rooms)
        occupied = sum(1 for r in rooms if r.status == RoomStatus.occupied)
        free = sum(1 for r in rooms if r.status == RoomStatus.free)
        pct = round(occupied / total * 100) if total else 0

        lines = [
            f"🏢 <b>Статус помещений</b>",
            f"Всего: {total} | Занято: {occupied} | Свободно: {free} | Заполненность: {pct}%\n",
        ]

        STATUS_ICON = {
            RoomStatus.occupied: "🔵",
            RoomStatus.free: "🟢",
            RoomStatus.reserved: "🟡",
            RoomStatus.repair: "🔴",
        }

        for floor_num in sorted(floors.keys()):
            floor_rooms = floors[floor_num]
            occ = sum(1 for r in floor_rooms if r.status == RoomStatus.occupied)
            fr = sum(1 for r in floor_rooms if r.status == RoomStatus.free)
            lines.append(f"<b>{floor_num} этаж</b> — занято {occ}/{len(floor_rooms)}, свободно {fr}")
            for r in floor_rooms:
                icon = STATUS_ICON.get(r.status, "⚪")
                lines.append(f"  {icon} {r.name} ({r.area} м²)")
            lines.append("")

        await send(chat_id, "\n".join(lines))
    finally:
        db.close()


async def cmd_debt(chat_id: str | int):
    """Задолженности арендаторов."""
    from app.database import SessionLocal
    from app.models.payment import Payment, PaymentStatus
    from app.models.contract import Contract
    from app.models.tenant import Tenant
    from app.models.room import Room

    db = SessionLocal()
    try:
        debts = db.query(Payment).filter(
            Payment.status.in_([PaymentStatus.debt, PaymentStatus.partial])
        ).all()

        if not debts:
            await send(chat_id, "✅ <b>Задолженностей нет!</b>\nВсе арендаторы платят вовремя.")
            return

        # Группируем по договору
        by_contract: dict[int, float] = {}
        for p in debts:
            d = p.amount_due - p.amount_paid
            by_contract[p.contract_id] = by_contract.get(p.contract_id, 0) + d

        lines = [f"🔴 <b>Задолженности арендаторов</b>\n"]
        total_debt = 0

        for contract_id, debt in sorted(by_contract.items(), key=lambda x: -x[1]):
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if not contract:
                continue
            tenant = db.query(Tenant).filter(Tenant.id == contract.tenant_id).first()
            room = db.query(Room).filter(Room.id == contract.room_id).first()
            lines.append(
                f"• <b>{tenant.name if tenant else '?'}</b> ({room.name if room else '?'})\n"
                f"  Долг: {int(debt):,} сом".replace(",", " ")
            )
            total_debt += debt

        lines.append(f"\n<b>Итого долг: {int(total_debt):,} сом</b>".replace(",", " "))
        await send(chat_id, "\n".join(lines))
    finally:
        db.close()


async def cmd_alerts(chat_id: str | int):
    """Краткая сводка уведомлений."""
    from app.database import SessionLocal
    from app.models.payment import Payment, PaymentStatus
    from app.models.contract import Contract, ContractStatus
    from app.models.tenant import Tenant
    from app.models.room import Room
    from datetime import datetime, timedelta

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        lines = [f"📬 <b>Уведомления — {now.strftime('%d.%m.%Y')}</b>\n"]

        # Долги
        debts = db.query(Payment).filter(
            Payment.status.in_([PaymentStatus.debt, PaymentStatus.partial])
        ).all()
        if debts:
            lines.append("🔴 <b>Просроченные платежи:</b>")
            by_contract: dict[int, float] = {}
            for p in debts:
                by_contract[p.contract_id] = by_contract.get(p.contract_id, 0) + (p.amount_due - p.amount_paid)
            for cid, d in sorted(by_contract.items(), key=lambda x: -x[1]):
                c = db.query(Contract).filter(Contract.id == cid).first()
                t = db.query(Tenant).filter(Tenant.id == c.tenant_id).first() if c else None
                r = db.query(Room).filter(Room.id == c.room_id).first() if c else None
                lines.append(f"  • {t.name if t else '?'} ({r.name if r else '?'}) — {int(d):,} сом".replace(",", " "))
        else:
            lines.append("✅ Просроченных платежей нет")

        lines.append("")

        # Истекающие договоры
        deadline = now + timedelta(days=30)
        expiring = db.query(Contract).filter(
            Contract.status.in_([ContractStatus.active, ContractStatus.expiring]),
            Contract.end_date <= deadline,
            Contract.end_date >= now,
        ).all()
        if expiring:
            lines.append("⚠️ <b>Договоры истекают (30 дней):</b>")
            for c in expiring:
                t = db.query(Tenant).filter(Tenant.id == c.tenant_id).first()
                r = db.query(Room).filter(Room.id == c.room_id).first()
                days = (c.end_date - now).days
                lines.append(f"  • {t.name if t else '?'} ({r.name if r else '?'}) — через {days} дн.")
        else:
            lines.append("✅ Истекающих договоров нет")

        await send(chat_id, "\n".join(lines), keyboard=MAIN_KEYBOARD)
    finally:
        db.close()


async def poll_loop():
    """Основной цикл polling — проверяет новые сообщения каждые 2 сек."""
    global _offset, _running
    _running = True

    while _running:
        try:
            async with httpx.AsyncClient(timeout=35) as client:
                r = await client.get(f"{BASE}/getUpdates", params={
                    "offset": _offset,
                    "timeout": 30,
                    "allowed_updates": ["message"],
                })
                if r.status_code == 200:
                    data = r.json()
                    for update in data.get("result", []):
                        _offset = update["update_id"] + 1
                        await handle_update(update)
        except Exception:
            await asyncio.sleep(5)


def stop():
    global _running
    _running = False
