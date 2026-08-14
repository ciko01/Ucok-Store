from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_api_key
from api.database import get_connection
from api.models import UserOut, TransactionOut, AddBalanceRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(limit: int = 50, offset: int = 0, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.user_id, u.username, u.full_name, u.first_seen_at, u.last_seen_at,
                   COALESCE(w.balance, 0) as balance
            FROM users u
            LEFT JOIN wallets w ON w.user_id = u.user_id
            ORDER BY u.first_seen_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [
        UserOut(
            user_id=r["user_id"],
            username=r["username"],
            full_name=r["full_name"],
            balance=r["balance"],
            first_seen_at=r["first_seen_at"],
            last_seen_at=r["last_seen_at"],
        )
        for r in rows
    ]


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        r = conn.execute(
            """
            SELECT u.user_id, u.username, u.full_name, u.first_seen_at, u.last_seen_at,
                   COALESCE(w.balance, 0) as balance
            FROM users u
            LEFT JOIN wallets w ON w.user_id = u.user_id
            WHERE u.user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return UserOut(
        user_id=r["user_id"],
        username=r["username"],
        full_name=r["full_name"],
        balance=r["balance"],
        first_seen_at=r["first_seen_at"],
        last_seen_at=r["last_seen_at"],
    )


@router.get("/{user_id}/transactions", response_model=list[TransactionOut])
def get_user_transactions(user_id: int, limit: int = 20, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
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


@router.post("/{user_id}/add-balance", response_model=UserOut)
def add_balance(user_id: int, data: AddBalanceRequest, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        user = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User tidak ditemukan")
        conn.execute(
            "INSERT INTO wallets (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP",
            (user_id, data.amount, data.amount),
        )
        conn.execute(
            "INSERT INTO transactions (user_id, description, transaction_type, amount) VALUES (?,?,?,?)",
            (user_id, data.description, "topup", data.amount),
        )
        conn.commit()
    return get_user(user_id, api_key)
