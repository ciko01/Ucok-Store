from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from api.auth import get_api_key
from api.database import get_connection
from api.models import SettingOut, SettingUpdate, AdminLogOut

router = APIRouter(prefix="/settings", tags=["settings"])


class QueueStatus(BaseModel):
    max_concurrent: int
    active: int
    queued: int
    active_users: list[int]
    queued_users: list[int]


@router.get("", response_model=list[SettingOut])
def list_settings(api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM bot_settings ORDER BY key").fetchall()
    return [SettingOut(key=r["key"], value=r["value"]) for r in rows]


@router.get("/{key}", response_model=SettingOut)
def get_setting(key: str, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        r = conn.execute("SELECT key, value FROM bot_settings WHERE key=?", (key,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Setting tidak ditemukan")
    return SettingOut(key=r["key"], value=r["value"])


@router.put("/{key}", response_model=SettingOut)
def upsert_setting(key: str, data: SettingUpdate, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO bot_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=?, updated_at=CURRENT_TIMESTAMP",
            (key, data.value, data.value),
        )
        conn.commit()
    return SettingOut(key=key, value=data.value)


@router.get("/queue/status", response_model=QueueStatus)
def get_queue_status(api_key: str = Depends(get_api_key)):
    try:
        from telegram_bot.queue_manager import get_status
        return QueueStatus(**get_status())
    except Exception:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT value FROM bot_settings WHERE key='max_concurrent_users'"
            ).fetchone()
        max_c = int(row["value"]) if row and row["value"].isdigit() else 0
        return QueueStatus(max_concurrent=max_c, active=0, queued=0, active_users=[], queued_users=[])


logs_router = APIRouter(prefix="/logs", tags=["logs"])


@logs_router.get("", response_model=list[AdminLogOut])
def list_logs(limit: int = 50, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        AdminLogOut(
            log_id=r["id"],
            admin_id=r["admin_id"],
            admin_name=r["admin_name"],
            action=r["action"],
            detail=r["detail"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
