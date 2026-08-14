from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_api_key
from api.database import get_connection
from api.models import TransactionOut

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    limit: int = 50,
    offset: int = 0,
    transaction_type: str | None = None,
    api_key: str = Depends(get_api_key),
):
    with get_connection() as conn:
        if transaction_type:
            rows = conn.execute(
                "SELECT * FROM transactions WHERE transaction_type=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (transaction_type, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    return [
        TransactionOut(
            transaction_id=r["id"],
            user_id=r["user_id"],
            description=r["description"],
            transaction_type=r["transaction_type"],
            amount=r["amount"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
