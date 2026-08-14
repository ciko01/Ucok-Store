from __future__ import annotations

import random
import string
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth import get_api_key
from api.database import get_connection
from telegram_bot.stats import (
    list_vouchers, get_voucher_by_code, get_voucher_claims, Voucher
)

router = APIRouter(prefix="/vouchers", tags=["vouchers"])


class VoucherOut(BaseModel):
    voucher_id: int
    code: str
    type: str
    amount: int
    max_claims: int
    claimed_count: int
    per_user: int
    is_active: bool
    expires_at: Optional[str]
    description: str
    created_at: str
    is_expired: bool
    remaining_claims: int


class VoucherCreate(BaseModel):
    code: Optional[str] = None
    type: str = "saldo"
    amount: int
    max_claims: int = 0
    per_user: int = 1
    expires_at: Optional[str] = None
    description: str = ""


class VoucherUpdate(BaseModel):
    amount: Optional[int] = None
    max_claims: Optional[int] = None
    per_user: Optional[int] = None
    is_active: Optional[bool] = None
    expires_at: Optional[str] = None
    description: Optional[str] = None


def _generate_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def _voucher_to_out(v: Voucher, created_at: str = "") -> VoucherOut:
    is_expired = False
    if v.expires_at:
        try:
            is_expired = datetime.utcnow() > datetime.fromisoformat(v.expires_at)
        except Exception:
            pass
    remaining = (v.max_claims - v.claimed_count) if v.max_claims > 0 else -1
    return VoucherOut(
        voucher_id=v.voucher_id, code=v.code, type=v.type, amount=v.amount,
        max_claims=v.max_claims, claimed_count=v.claimed_count, per_user=v.per_user,
        is_active=v.is_active, expires_at=v.expires_at, description=v.description,
        created_at=created_at, is_expired=is_expired,
        remaining_claims=remaining,
    )


@router.get("", response_model=list[VoucherOut])
def get_vouchers(active_only: bool = False, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        q = "SELECT * FROM vouchers"
        if active_only:
            q += " WHERE is_active = 1"
        q += " ORDER BY created_at DESC"
        rows = conn.execute(q).fetchall()
    result = []
    for r in rows:
        v = Voucher(r["id"], r["code"], r["type"], r["amount"], r["max_claims"],
                    r["claimed_count"], r["per_user"], bool(r["is_active"]),
                    r["expires_at"], r["description"])
        result.append(_voucher_to_out(v, r["created_at"]))
    return result


@router.post("", response_model=VoucherOut, status_code=201)
def create_voucher(data: VoucherCreate, api_key: str = Depends(get_api_key)):
    code = (data.code or _generate_code()).upper().strip()
    if get_voucher_by_code(code):
        raise HTTPException(status_code=400, detail="Kode sudah dipakai")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO vouchers (code, type, amount, max_claims, per_user, expires_at, description) VALUES (?,?,?,?,?,?,?)",
            (code, data.type, data.amount, data.max_claims, data.per_user, data.expires_at, data.description),
        )
        vid = cur.lastrowid
        conn.commit()
        r = conn.execute("SELECT * FROM vouchers WHERE id=?", (vid,)).fetchone()
    v = Voucher(r["id"], r["code"], r["type"], r["amount"], r["max_claims"],
                r["claimed_count"], r["per_user"], bool(r["is_active"]),
                r["expires_at"], r["description"])
    return _voucher_to_out(v, r["created_at"])


@router.post("/generate", response_model=list[VoucherOut], status_code=201)
def generate_vouchers(data: VoucherCreate, count: int = 1, api_key: str = Depends(get_api_key)):
    """Generate beberapa voucher sekaligus dengan kode random."""
    if count < 1 or count > 500:
        raise HTTPException(status_code=400, detail="Count harus 1-500")
    results = []
    with get_connection() as conn:
        for _ in range(count):
            for _ in range(10):
                code = _generate_code()
                existing = conn.execute("SELECT id FROM vouchers WHERE UPPER(code)=?", (code,)).fetchone()
                if not existing:
                    break
            cur = conn.execute(
                "INSERT INTO vouchers (code, type, amount, max_claims, per_user, expires_at, description) VALUES (?,?,?,?,?,?,?)",
                (code, data.type, data.amount, data.max_claims, data.per_user, data.expires_at, data.description),
            )
            vid = cur.lastrowid
            r = conn.execute("SELECT * FROM vouchers WHERE id=?", (vid,)).fetchone()
            v = Voucher(r["id"], r["code"], r["type"], r["amount"], r["max_claims"],
                        r["claimed_count"], r["per_user"], bool(r["is_active"]),
                        r["expires_at"], r["description"])
            results.append(_voucher_to_out(v, r["created_at"]))
        conn.commit()
    return results


@router.patch("/{voucher_id}", response_model=VoucherOut)
def update_voucher(voucher_id: int, data: VoucherUpdate, api_key: str = Depends(get_api_key)):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Tidak ada field yang diupdate")
    if "is_active" in fields:
        fields["is_active"] = 1 if fields["is_active"] else 0
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(f"UPDATE vouchers SET {set_clause} WHERE id=?", (*fields.values(), voucher_id))
        conn.commit()
        r = conn.execute("SELECT * FROM vouchers WHERE id=?", (voucher_id,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Voucher tidak ditemukan")
    v = Voucher(r["id"], r["code"], r["type"], r["amount"], r["max_claims"],
                r["claimed_count"], r["per_user"], bool(r["is_active"]),
                r["expires_at"], r["description"])
    return _voucher_to_out(v, r["created_at"])


@router.delete("/{voucher_id}", status_code=204)
def delete_voucher(voucher_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        conn.execute("DELETE FROM voucher_claims WHERE voucher_id=?", (voucher_id,))
        conn.execute("DELETE FROM vouchers WHERE id=?", (voucher_id,))
        conn.commit()


@router.get("/{voucher_id}/claims")
def get_claims(voucher_id: int, api_key: str = Depends(get_api_key)):
    return get_voucher_claims(voucher_id)
