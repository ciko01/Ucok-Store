from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    bot_name: str
    banner_path: Path
    admin_ids: set[int]


def load_settings() -> Settings:
    load_dotenv()
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    bot_name = os.getenv("BOT_NAME", "TEHTARIK").strip() or "TEHTARIK"
    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN belum diisi. Tambahkan ke file .env.")
    admin_ids = {
        int(item.strip())
        for item in admin_ids_raw.split(",")
        if item.strip().isdigit()
    }
    return Settings(
        bot_token=bot_token,
        bot_name=bot_name,
        banner_path=Path("assets") / "start-banner.jpg",
        admin_ids=admin_ids,
    )
