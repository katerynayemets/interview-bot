# app/worker/telegram_api.py
import httpx
from app.config import settings


def send_message(chat_id: int, text: str) -> None:
    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    # Telegram лимит ~4096
    chunks = []
    t = text or ""
    while t:
        chunks.append(t[:4000])
        t = t[4000:]

    with httpx.Client(timeout=20) as client:
        for chunk in chunks:
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            r = client.post(url, json=payload)
            r.raise_for_status()
