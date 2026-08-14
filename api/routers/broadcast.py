from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_api_key
from api.database import get_connection
from api.bot_instance import broadcast_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/broadcast", tags=["broadcast"])


class BroadcastRequest(BaseModel):
    message: str
    parse_mode: str = "HTML"


class BroadcastResult(BaseModel):
    total: int
    success: int
    failed: int


@router.post("", response_model=BroadcastResult)
def send_broadcast(data: BroadcastRequest, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute("SELECT user_id FROM users ORDER BY user_id").fetchall()
    user_ids = [r["user_id"] for r in rows]
    if not user_ids:
        return BroadcastResult(total=0, success=0, failed=0)
    result = broadcast_sync(user_ids, data.message, data.parse_mode)
    return BroadcastResult(**result)
