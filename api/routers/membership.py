from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.auth import get_api_key
from api.database import get_connection
from api.bot_instance import send_message_sync
from telegram_bot.stats import (
    get_membership_tiers, get_user_membership, set_user_membership,
    get_all_user_memberships, MembershipTier, UserMembership,
)

router = APIRouter(prefix="/membership", tags=["membership"])


class TierOut(BaseModel):
    tier_id: int
    name: str
    duration_days: int
    discount_percent: int
    bonus_multiplier: float
    skip_queue: bool
    badge: str


class TierUpdate(BaseModel):
    duration_days: Optional[int] = None
    discount_percent: Optional[int] = None
    bonus_multiplier: Optional[float] = None
    skip_queue: Optional[bool] = None
    badge: Optional[str] = None


class UserMembershipOut(BaseModel):
    user_id: int
    full_name: str
    username: Optional[str]
    tier_name: str
    badge: str
    discount_percent: int
    bonus_multiplier: float
    skip_queue: bool
    activated_at: str
    expires_at: Optional[str]
    is_active: bool


class SetMemberRequest(BaseModel):
    tier_name: str


def _tier_to_out(t: MembershipTier) -> TierOut:
    return TierOut(
        tier_id=t.tier_id, name=t.name, duration_days=t.duration_days,
        discount_percent=t.discount_percent, bonus_multiplier=t.bonus_multiplier,
        skip_queue=t.skip_queue, badge=t.badge,
    )


@router.get("/tiers", response_model=list[TierOut])
def list_tiers(api_key: str = Depends(get_api_key)):
    return [_tier_to_out(t) for t in get_membership_tiers()]


@router.patch("/tiers/{tier_id}", response_model=TierOut)
def update_tier(tier_id: int, data: TierUpdate, api_key: str = Depends(get_api_key)):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Tidak ada field yang diupdate")
    if "skip_queue" in fields:
        fields["skip_queue"] = 1 if fields["skip_queue"] else 0
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(f"UPDATE membership_tiers SET {set_clause} WHERE id=?", (*fields.values(), tier_id))
        conn.commit()
    tiers = get_membership_tiers()
    t = next((t for t in tiers if t.tier_id == tier_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Tier tidak ditemukan")
    return _tier_to_out(t)


@router.get("/users", response_model=list[UserMembershipOut])
def list_user_memberships(api_key: str = Depends(get_api_key)):
    rows = get_all_user_memberships()
    result = []
    for r in rows:
        m = get_user_membership(r["user_id"])
        result.append(UserMembershipOut(
            user_id=r["user_id"], full_name=r["full_name"], username=r["username"],
            tier_name=r["tier_name"], badge=r["badge"],
            discount_percent=r["discount_percent"], bonus_multiplier=r["bonus_multiplier"],
            skip_queue=r["skip_queue"], activated_at=r["activated_at"],
            expires_at=r["expires_at"], is_active=m.is_active,
        ))
    return result


@router.get("/users/{user_id}", response_model=UserMembershipOut)
def get_user_membership_api(user_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        u = conn.execute("SELECT full_name, username FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    m = get_user_membership(user_id)
    return UserMembershipOut(
        user_id=user_id, full_name=u["full_name"], username=u["username"],
        tier_name=m.tier_name, badge=m.badge,
        discount_percent=m.discount_percent, bonus_multiplier=m.bonus_multiplier,
        skip_queue=m.skip_queue, activated_at=m.activated_at,
        expires_at=m.expires_at, is_active=m.is_active,
    )


@router.post("/users/{user_id}", response_model=UserMembershipOut)
def set_membership(user_id: int, data: SetMemberRequest, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        u = conn.execute("SELECT full_name, username FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    try:
        m = set_user_membership(user_id, data.tier_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    exp_str = m.expires_at[:10] if m.expires_at else "Selamanya"
    benefits = []
    if m.discount_percent > 0:
        benefits.append(f"🏷️ Diskon {m.discount_percent}% semua produk")
    if m.bonus_multiplier > 1.0:
        benefits.append(f"🎁 Bonus harian ×{m.bonus_multiplier}")
    if m.skip_queue:
        benefits.append("⚡ Prioritas antrian")
    benefit_text = "\n".join(f"  {b}" for b in benefits) if benefits else "  Tidak ada benefit khusus"

    send_message_sync(
        user_id,
        f"🎉 <b>Membership Diaktifkan!</b>\n\n"
        f"{m.badge} Kamu sekarang adalah member <b>{m.tier_name}</b>!\n"
        f"📅 Berlaku hingga: {exp_str}\n\n"
        f"<b>Benefit kamu:</b>\n{benefit_text}",
    )

    return UserMembershipOut(
        user_id=user_id, full_name=u["full_name"], username=u["username"],
        tier_name=m.tier_name, badge=m.badge,
        discount_percent=m.discount_percent, bonus_multiplier=m.bonus_multiplier,
        skip_queue=m.skip_queue, activated_at=m.activated_at,
        expires_at=m.expires_at, is_active=m.is_active,
    )
