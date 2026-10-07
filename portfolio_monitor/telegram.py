"""Send plain-text messages through a Telegram bot."""

import requests

MAX_LEN = 4096  # Telegram's per-message limit


def split_message(text: str, limit: int = MAX_LEN) -> list[str]:
    chunks = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        chunks.append(text)
    return chunks


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for chunk in split_message(text):
        resp = requests.post(url, json={"chat_id": chat_id, "text": chunk}, timeout=30)
        if not resp.ok:
            # Don't echo the URL: it contains the bot token.
            raise RuntimeError(f"Telegram sendMessage failed ({resp.status_code}): {resp.text[:300]}")
