from __future__ import annotations

import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)

_active_users: set[int] = set()
_waiting_queue: dict[int, asyncio.Event] = {}

DEFAULT_MAX = 0


def get_max_concurrent() -> int:
    """Baca max_concurrent_users dari database. 0 = tidak dibatasi."""
    try:
        from telegram_bot.stats import get_setting
        val = get_setting("max_concurrent_users", "0").strip()
        return max(0, int(val)) if val.isdigit() else 0
    except Exception:
        return 0


def active_count() -> int:
    return len(_active_users)


def queue_count() -> int:
    return len(_waiting_queue)


async def acquire(user_id: int) -> None:
    """
    Coba masuk slot aktif. Jika penuh, tunggu sampai ada slot kosong.
    user_id < 0 = admin, tidak pernah diblokir.
    Member dengan skip_queue = langsung masuk tanpa antri.
    """
    max_c = get_max_concurrent()
    if max_c <= 0 or user_id < 0:
        _active_users.add(user_id)
        return

    if user_id in _active_users:
        return

    # Cek membership — skip queue jika tier membolehkan
    try:
        from telegram_bot.stats import get_user_membership
        membership = get_user_membership(user_id)
        if membership.is_active and membership.skip_queue:
            _active_users.add(user_id)
            return
    except Exception:
        pass

    while len(_active_users) >= max_c:
        event = asyncio.Event()
        _waiting_queue[user_id] = event
        logger.debug("User %d menunggu slot (aktif: %d/%d)", user_id, len(_active_users), max_c)
        await event.wait()
        _waiting_queue.pop(user_id, None)

    _active_users.add(user_id)


def release(user_id: int) -> None:
    """Lepaskan slot aktif dan beri tahu user berikutnya dalam antrian."""
    _active_users.discard(user_id)
    if _waiting_queue:
        next_uid, event = next(iter(_waiting_queue.items()))
        logger.debug("Slot tersedia, beri tahu user %d", next_uid)
        event.set()


def get_status() -> dict:
    return {
        "max_concurrent": get_max_concurrent(),
        "active": len(_active_users),
        "queued": len(_waiting_queue),
        "active_users": list(_active_users),
        "queued_users": list(_waiting_queue.keys()),
    }
