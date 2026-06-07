import httpx
from app.config import settings

BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}"


async def send_message(chat_id: str, text: str) -> bool:
    """Отправить сообщение в Telegram. Возвращает True при успехе."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{BASE}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })
        return r.status_code == 200


async def get_updates() -> list[dict]:
    """Получить последние обновления (для определения chat_id)."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE}/getUpdates", params={"limit": 10, "timeout": 1})
        if r.status_code == 200:
            return r.json().get("result", [])
        return []


async def get_chat_id_from_updates() -> str | None:
    """Найти chat_id из последних сообщений боту."""
    updates = await get_updates()
    for u in reversed(updates):
        msg = u.get("message") or u.get("channel_post")
        if msg:
            return str(msg["chat"]["id"])
    return None
