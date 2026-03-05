"""Telegram bot output for transcribed notes.

Sends full notes to Telegram with rich text formatting.
Uses stdlib only (urllib) — no extra dependencies.
Chat ID auto-discovered via getUpdates on first message.
"""

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

import config

logger = logging.getLogger(__name__)

CHAT_ID_FILE = Path(__file__).parent / ".telegram_chat_id"

# Telegram message limit
MAX_MESSAGE_LENGTH = 4096

# Sentiment indicators
SENTIMENT_ICONS = {
    "positive": "\u2600\ufe0f",   # ☀️
    "neutral": "\u25cb",          # ○
    "reflective": "\U0001f4ad",   # 💭
    "negative": "\u26c8\ufe0f",   # ⛈️
}

# Mode headers
MODE_HEADERS = {
    "checkin": "\U0001f7e2 CHECK-IN",    # 🟢
    "checkout": "\U0001f534 CHECK-OUT",   # 🔴
}


def _telegram_api(method: str, data: dict) -> dict | None:
    """Call Telegram Bot API."""
    token = getattr(config, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        return None

    url = f"https://api.telegram.org/bot{token}/{method}"
    payload = json.dumps(data).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error(f"Telegram API error ({e.code}): {body}")
        return None
    except Exception as e:
        logger.error(f"Telegram request failed: {e}")
        return None


def _get_chat_id() -> str | None:
    """Get chat ID from file or auto-discover via getUpdates."""
    # Check saved file
    if CHAT_ID_FILE.exists():
        chat_id = CHAT_ID_FILE.read_text().strip()
        if chat_id:
            return chat_id

    # Auto-discover from recent messages
    logger.info("Discovering Telegram chat ID via getUpdates...")
    result = _telegram_api("getUpdates", {"limit": 10})
    if not result or not result.get("ok"):
        logger.warning("Could not get Telegram updates. Send /start to the bot first.")
        return None

    updates = result.get("result", [])
    if not updates:
        logger.warning("No Telegram messages found. Send /start to the bot first.")
        return None

    # Find most recent update with a "message" key
    for update in reversed(updates):
        if "message" in update and "chat" in update["message"]:
            chat_id = str(update["message"]["chat"]["id"])
            CHAT_ID_FILE.write_text(chat_id)
            logger.info(f"Saved Telegram chat ID: {chat_id}")
            return chat_id

    logger.warning("No usable Telegram messages found. Send /start to the bot first.")
    return None


def _escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_note(
    text: str,
    topic: str,
    checkin_checkout_mode: str | None,
    sentiment: str,
    language: str,
    duration: str,
) -> str:
    """Format note as Telegram HTML rich text."""
    parts = []

    # Header line: mode or generic
    if checkin_checkout_mode and checkin_checkout_mode in MODE_HEADERS:
        header = MODE_HEADERS[checkin_checkout_mode]
    else:
        header = "\U0001f3a4 AUDIO NOTE"  # 🎤

    parts.append(f"<b>{header}</b>")

    # Metadata line: sentiment + language + duration
    sentiment_icon = SENTIMENT_ICONS.get(sentiment, "\u25cb")
    meta_parts = [f"{sentiment_icon} {sentiment}"]
    if language:
        meta_parts.append(language.upper())
    if duration and duration != "unknown":
        meta_parts.append(f"\u23f1 {duration}")  # ⏱
    parts.append("<i>" + " \u00b7 ".join(meta_parts) + "</i>")

    # Separator
    parts.append("")

    # Full note text
    parts.append(_escape_html(text))

    return "\n".join(parts)


def _send_message(chat_id: str, text: str) -> bool:
    """Send a single message, splitting if too long."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        result = _telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })
        return result is not None and result.get("ok", False)

    # Split long messages at paragraph boundaries
    margin = 50  # reserve for "continued" label
    limit = MAX_MESSAGE_LENGTH - margin
    chunks = []
    current = ""
    for line in text.split("\n"):
        candidate = current + "\n" + line if current else line
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            # Handle single lines longer than the limit
            while len(line) > limit:
                chunks.append(line[:limit])
                line = line[limit:]
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)

    success = True
    for i, chunk in enumerate(chunks):
        if i > 0:
            chunk = f"<i>...continued ({i + 1}/{len(chunks)})</i>\n\n{chunk}"
        result = _telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
        })
        if not result or not result.get("ok"):
            success = False
    return success


def send_alert(text: str) -> bool:
    """Send an alert message to Telegram. Never raises."""
    if not getattr(config, "TELEGRAM_ENABLED", False):
        return False

    token = getattr(config, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
        return False

    chat_id = _get_chat_id()
    if not chat_id:
        return False

    try:
        return _send_message(chat_id, text)
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")
        return False


def send_note(
    text: str,
    topic: str = "",
    checkin_checkout_mode: str | None = None,
    sentiment: str = "neutral",
    language: str = "",
    duration: str = "",
) -> bool:
    """Send a transcribed note to Telegram.

    Returns True if sent successfully, False otherwise.
    Never raises — notification failures must not affect the service.
    """
    if not getattr(config, "TELEGRAM_ENABLED", False):
        return False

    token = getattr(config, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
        return False

    chat_id = _get_chat_id()
    if not chat_id:
        return False

    try:
        message = _format_note(
            text, topic, checkin_checkout_mode, sentiment, language, duration
        )
        return _send_message(chat_id, message)
    except Exception as e:
        # Never let Telegram failures affect the transcription service
        logger.error(f"Telegram send failed: {e}")
        return False
