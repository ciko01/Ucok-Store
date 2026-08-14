from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class ProductOut(BaseModel):
    product_id: int
    name: str
    category: str
    price: int
    description: str
    available_stock: int
    custom_id: str
    has_variants: bool
    is_active: bool
    stock_source: str = "database"
    stock_config: str = ""


class ProductCreate(BaseModel):
    name: str
    category: str
    price: int
    description: str = ""
    custom_id: str = ""
    stock_source: str = "database"
    stock_config: str = ""


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    description: Optional[str] = None
    custom_id: Optional[str] = None
    is_active: Optional[bool] = None
    stock_source: Optional[str] = None
    stock_config: Optional[str] = None


class VariantOut(BaseModel):
    variant_id: int
    product_id: int
    name: str
    price: int
    custom_id: str
    available_stock: int
    stock_source: str = "database"
    stock_config: str = ""


class VariantCreate(BaseModel):
    name: str
    price: int
    custom_id: str = ""
    stock_source: str = "database"
    stock_config: str = ""


class VariantUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[int] = None
    custom_id: Optional[str] = None
    stock_source: Optional[str] = None
    stock_config: Optional[str] = None


class StockItemOut(BaseModel):
    stock_id: int
    product_id: int
    variant_id: int
    content: str
    status: str
    delivered_to_user_id: Optional[int]
    delivered_at: Optional[str]
    created_at: str


class UserOut(BaseModel):
    user_id: int
    username: Optional[str]
    full_name: str
    balance: int
    first_seen_at: str
    last_seen_at: str


class TransactionOut(BaseModel):
    transaction_id: int
    user_id: int
    description: Optional[str]
    transaction_type: str
    amount: int
    created_at: str


class TopUpRequestOut(BaseModel):
    request_id: int
    user_id: int
    full_name: str
    username: Optional[str]
    amount: int
    proof_file_id: str
    status: str
    created_at: str


class TopUpRequestCreate(BaseModel):
    user_id: int
    amount: int
    proof_file_id: str


class TopUpAction(BaseModel):
    action: str


class BankOut(BaseModel):
    bank_id: int
    bank_name: str
    account_number: str
    account_holder: str
    notes: str
    is_active: bool


class BankCreate(BaseModel):
    bank_name: str
    account_number: str
    account_holder: str
    notes: str = ""


class BankUpdate(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class StatsOut(BaseModel):
    total_users: int
    total_transactions: int
    total_revenue: int
    total_products: int
    pending_topups: int


class RevenuePoint(BaseModel):
    date: str
    revenue: int
    transactions: int


class AdminLogOut(BaseModel):
    log_id: int
    admin_id: int
    admin_name: str
    action: str
    detail: str
    created_at: str


class SettingOut(BaseModel):
    key: str
    value: str


class SettingUpdate(BaseModel):
    value: str


class AddBalanceRequest(BaseModel):
    user_id: int
    amount: int
    description: str = "Top-up via webapp"


class TopBuyerOut(BaseModel):
    rank: int
    full_name: str
    username: Optional[str]
    total_spent: int
    total_purchases: int
