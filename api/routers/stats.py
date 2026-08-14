from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_api_key
from api.database import get_connection
from api.models import StatsOut, RevenuePoint, TopBuyerOut

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_transactions = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_type = 'purchase'"
        ).fetchone()[0]
        total_revenue = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE transaction_type = 'purchase'"
        ).fetchone()[0]
        total_products = conn.execute(
            "SELECT COUNT(*) FROM products WHERE is_active = 1"
        ).fetchone()[0]
        pending_topups = conn.execute(
            "SELECT COUNT(*) FROM topup_requests WHERE status = 'pending'"
        ).fetchone()[0]
    return StatsOut(
        total_users=total_users,
        total_transactions=total_transactions,
        total_revenue=total_revenue,
        total_products=total_products,
        pending_topups=pending_topups,
    )


@router.get("/revenue", response_model=list[RevenuePoint])
def get_revenue(days: int = 30, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT DATE(created_at) as date,
                   COALESCE(SUM(amount), 0) as revenue,
                   COUNT(*) as transactions
            FROM transactions
            WHERE transaction_type = 'purchase'
              AND created_at >= DATE('now', ? || ' days')
            GROUP BY DATE(created_at)
            ORDER BY date ASC
            """,
            (f"-{days}",),
        ).fetchall()
    return [RevenuePoint(date=r["date"], revenue=r["revenue"], transactions=r["transactions"]) for r in rows]


@router.get("/top-buyers", response_model=list[TopBuyerOut])
def get_top_buyers(limit: int = 10, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT u.full_name, u.username,
                   COALESCE(SUM(t.amount), 0) as total_spent,
                   COUNT(t.id) as total_purchases
            FROM users u
            JOIN transactions t ON t.user_id = u.user_id
            WHERE t.transaction_type = 'purchase'
            GROUP BY u.user_id
            ORDER BY total_spent DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        TopBuyerOut(
            rank=i + 1,
            full_name=r["full_name"],
            username=r["username"],
            total_spent=r["total_spent"],
            total_purchases=r["total_purchases"],
        )
        for i, r in enumerate(rows)
    ]
