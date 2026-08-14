from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

# {user_id: {handler_name: last_call_time}}
_cooldowns: dict[int, dict[str, float]] = defaultdict(dict)

DEFAULT_COOLDOWN = 1.5  # detik antar request


def rate_limit(seconds: float = DEFAULT_COOLDOWN):
    """Decorator: batasi frekuensi handler per user.
    Jika user kirim terlalu cepat, request diabaikan (tanpa pesan error).
    Admin tidak kena rate limit.
    """
    def decorator(handler):
        @functools.wraps(handler)
        async def wrapper(update, context):
            from telegram_bot.handlers import _is_admin
            user = update.effective_user
            if user is None or _is_admin(update, context):
                return await handler(update, context)

            uid = user.id
            key = handler.__name__
            now = time.monotonic()
            last = _cooldowns[uid].get(key, 0)

            if now - last < seconds:
                if update.callback_query:
                    try:
                        await update.callback_query.answer()
                    except Exception:
                        pass
                return

            _cooldowns[uid][key] = now
            return await handler(update, context)
        return wrapper
    return decorator


def cleanup_cooldowns() -> None:
    """Bersihkan entri cooldown yang sudah lama (panggil berkala)."""
    now = time.monotonic()
    cutoff = 300  # 5 menit
    to_del = [uid for uid, data in _cooldowns.items()
              if all(now - t > cutoff for t in data.values())]
    for uid in to_del:
        del _cooldowns[uid]
