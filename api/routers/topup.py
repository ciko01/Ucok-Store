from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_api_key
from api.database import get_connection
from api.models import TopUpRequestOut
from api.bot_instance import send_message_sync
from telegram_bot.messages import format_rupiah
from telegram_bot.stats import get_user_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/topup", tags=["topup"])


def _send_telegram(user_id: int, text: str) -> None:
    send_message_sync(user_id, text)


@router.get("", response_model=list[TopUpRequestOut])
def list_topup_requests(status: str = "pending", api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT t.id, t.user_id, u.full_name, u.username, t.amount,
                   t.proof_file_id, t.status, t.created_at
            FROM topup_requests t
            JOIN users u ON u.user_id = t.user_id
            WHERE t.status = ?
            ORDER BY t.created_at DESC
            """,
            (status,),
        ).fetchall()
    return [_row_to_out(r) for r in rows]


@router.post("/{request_id}/approve", response_model=TopUpRequestOut)
def approve_topup(request_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        req = _fetch_request(conn, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request tidak ditemukan")
        if req["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Request sudah {req['status']}")
        conn.execute(
            "UPDATE topup_requests SET status='approved', reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (request_id,),
        )
        conn.execute(
            "INSERT INTO wallets (user_id, balance) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET balance=balance+?, updated_at=CURRENT_TIMESTAMP",
            (req["user_id"], req["amount"], req["amount"]),
        )
        conn.execute(
            "INSERT INTO transactions (user_id, description, transaction_type, amount) VALUES (?,?,?,?)",
            (req["user_id"], f"Top-up disetujui (ID #{request_id})", "topup", req["amount"]),
        )
        conn.commit()
        updated = _fetch_request(conn, request_id)

    profile = get_user_profile(req["user_id"])
    new_balance = profile.balance if profile else 0
    _send_telegram(
        req["user_id"],
        f"✅ <b>Top Up Berhasil!</b>\n\n"
        f"💰 Jumlah    : {format_rupiah(req['amount'])}\n"
        f"💳 Saldo baru: {format_rupiah(new_balance)}\n\n"
        f"Terima kasih sudah top up! Selamat belanja 🛒",
    )
    return _row_to_out(updated)


@router.post("/{request_id}/reject", response_model=TopUpRequestOut)
def reject_topup(request_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        req = _fetch_request(conn, request_id)
        if not req:
            raise HTTPException(status_code=404, detail="Request tidak ditemukan")
        if req["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Request sudah {req['status']}")
        conn.execute(
            "UPDATE topup_requests SET status='rejected', reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (request_id,),
        )
        conn.commit()
        updated = _fetch_request(conn, request_id)

    _send_telegram(
        req["user_id"],
        f"❌ <b>Top Up Ditolak</b>\n\n"
        f"Permintaan top up sebesar {format_rupiah(req['amount'])} ditolak oleh admin.\n"
        f"Silakan hubungi admin jika ada pertanyaan.",
    )
    return _row_to_out(updated)
