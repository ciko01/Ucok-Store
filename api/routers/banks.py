from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_api_key
from api.database import get_connection
from api.models import BankOut, BankCreate, BankUpdate

router = APIRouter(prefix="/banks", tags=["banks"])


@router.get("", response_model=list[BankOut])
def list_banks(active_only: bool = False, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        query = "SELECT * FROM banks"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY id"
        rows = conn.execute(query).fetchall()
    return [
        BankOut(
            bank_id=r["id"],
            bank_name=r["bank_name"],
            account_number=r["account_number"],
            account_holder=r["account_holder"],
            notes=r["notes"],
            is_active=bool(r["is_active"]),
        )
        for r in rows
    ]


@router.post("", response_model=BankOut, status_code=201)
def create_bank(data: BankCreate, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO banks (bank_name, account_number, account_holder, notes) VALUES (?,?,?,?)",
            (data.bank_name, data.account_number, data.account_holder, data.notes),
        )
        bank_id = cur.lastrowid
        conn.commit()
        r = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    return BankOut(
        bank_id=r["id"],
        bank_name=r["bank_name"],
        account_number=r["account_number"],
        account_holder=r["account_holder"],
        notes=r["notes"],
        is_active=bool(r["is_active"]),
    )


@router.patch("/{bank_id}", response_model=BankOut)
def update_bank(bank_id: int, data: BankUpdate, api_key: str = Depends(get_api_key)):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Tidak ada field yang diupdate")
    if "is_active" in fields:
        fields["is_active"] = 1 if fields["is_active"] else 0
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(f"UPDATE banks SET {set_clause} WHERE id=?", (*fields.values(), bank_id))
        conn.commit()
        r = conn.execute("SELECT * FROM banks WHERE id=?", (bank_id,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail="Bank tidak ditemukan")
    return BankOut(
        bank_id=r["id"],
        bank_name=r["bank_name"],
        account_number=r["account_number"],
        account_holder=r["account_holder"],
        notes=r["notes"],
        is_active=bool(r["is_active"]),
    )


@router.delete("/{bank_id}", status_code=204)
def delete_bank(bank_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        conn.execute("DELETE FROM banks WHERE id=?", (bank_id,))
        conn.commit()
