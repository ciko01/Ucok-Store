from __future__ import annotations

import asyncio
import logging
from typing import Optional
from telegram import Bot

logger = logging.getLogger(__name__)

_bot: Optional[Bot] = None
_loop: Optional[asyncio.AbstractEventLoop] = None


def set_bot(bot: Bot, loop: asyncio.AbstractEventLoop) -> None:
    global _bot, _loop
    _bot = bot
    _loop = loop


def get_bot() -> Optional[Bot]:
    return _bot


def send_message_sync(chat_id: int, text: str, parse_mode: str = "HTML") -> None:
    """Kirim pesan Telegram dari sync context (FastAPI thread) ke bot event loop."""
    if _bot is None or _loop is None:
        logger.warning("Bot belum tersedia, pesan tidak dikirim ke %s", chat_id)
        return
    if _loop.is_closed():
        logger.warning("Bot event loop sudah tertutup, pesan tidak dikirim ke %s", chat_id)
        return
    try:
        future = asyncio.run_coroutine_threadsafe(
            _bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode),
            _loop,
        )
        future.result(timeout=15)
    except Exception as e:
        logger.warning("Gagal kirim pesan ke %s: %s", chat_id, e)


def broadcast_sync(user_ids: list[int], text: str, parse_mode: str = "HTML") -> dict:
    """Broadcast ke banyak user dari sync context."""
    if _bot is None or _loop is None:
        return {"total": len(user_ids), "success": 0, "failed": len(user_ids)}
    success = 0
    failed = 0
    for uid in user_ids:
        try:
            future = asyncio.run_coroutine_threadsafe(
                _bot.send_message(chat_id=uid, text=text, parse_mode=parse_mode),
                _loop,
            )
            future.result(timeout=10)
            success += 1
        except Exception as e:
            logger.debug("Broadcast gagal ke %s: %s", uid, e)
            failed += 1
    return {"total": len(user_ids), "success": success, "failed": failed}
