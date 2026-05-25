from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from pathlib import Path


DB_PATH = Path("bot_data.sqlite3")

# Threshold stok rendah — notifikasi admin jika stok <= nilai ini
LOW_STOCK_THRESHOLD = 3

# Daily bonus configuration
DAILY_BONUS_BASE = 500
DAILY_BONUS_STEP = 500
DAILY_BONUS_MAX_STREAK = 7  # streak cap untuk hitungan reward


@dataclass(frozen=True)
class BotStats:
    total_users: int
    total_transactions: int
    total_revenue: int


@dataclass(frozen=True)
class UserProfile:
    user_id: int
    username: str | None
    full_name: str
    balance: int


@dataclass(frozen=True)
class Product:
    product_id: int
    name: str
    category: str
    price: int
    description: str
    is_active: bool


@dataclass(frozen=True)
class ProductSummary:
    product_id: int
    name: str
    category: str
    price: int
    description: str
    available_stock: int


@dataclass(frozen=True)
class TransactionRecord:
    transaction_id: int
    description: str
    transaction_type: str
    amount: int
    created_at: str


@dataclass(frozen=True)
class TopBuyerRecord:
    rank: int
    full_name: str
    username: str | None
    total_spent: int
    total_purchases: int


@dataclass(frozen=True)
class TopUpRequest:
    request_id: int
    user_id: int
    full_name: str
    username: str | None
    amount: int
    proof_file_id: str
    status: str
    created_at: str


@dataclass(frozen=True)
class AdminLog:
    log_id: int
    admin_id: int
    admin_name: str
    action: str
    detail: str
    created_at: str


@dataclass(frozen=True)
class Bank:
    bank_id: int
    bank_name: str
    account_number: str
    account_holder: str
    notes: str
    is_active: bool


@dataclass(frozen=True)
class DailyBonusInfo:
    success: bool
    already_claimed: bool
    claimed_amount: int
    streak: int
    next_amount: int
    new_balance: int
    next_claim_at: str  # "besok" atau ISO date


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")   # lebih aman untuk concurrent writes
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS wallets (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT,
                transaction_type TEXT NOT NULL DEFAULT 'info',
                amount INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price INTEGER NOT NULL DEFAULT 0,
                description TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS product_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                delivered_to_user_id INTEGER,
                delivered_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id, content),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS topup_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                proof_file_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by INTEGER,
                reviewed_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )
        # ── BARU: log aktivitas admin ─────────────────────────────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                admin_name TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # ── BARU: pending checkout (konfirmasi sebelum bayar) ─────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pending_checkouts (
                user_id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ── v7: key-value settings (maintenance mode, dll) ────────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # ── v7: daftar rekening bank dinamis ──────────────────────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS banks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT NOT NULL,
                account_number TEXT NOT NULL,
                account_holder TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        # ── v7: daily login bonus tracking ────────────────────────────────────
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_bonus_claims (
                user_id INTEGER PRIMARY KEY,
                last_claim_date TEXT NOT NULL,
                streak INTEGER NOT NULL DEFAULT 1,
                total_claimed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            """
        )

        _run_migrations(connection)
        _seed_default_banks(connection)


def _run_migrations(connection: sqlite3.Connection) -> None:
    """Tambah kolom baru ke tabel yang sudah ada jika belum ada (idempotent)."""
    existing_trx_cols = {
        row[1]
        for row in connection.execute("PRAGMA table_info(transactions)").fetchall()
    }
    if "transaction_type" not in existing_trx_cols:
        connection.execute(
            "ALTER TABLE transactions ADD COLUMN transaction_type TEXT NOT NULL DEFAULT 'info'"
        )
    if "description" not in existing_trx_cols:
        connection.execute(
            "ALTER TABLE transactions ADD COLUMN description TEXT"
        )

    existing_product_cols = {
        row[1]
        for row in connection.execute("PRAGMA table_info(products)").fetchall()
    }
    if "is_active" not in existing_product_cols:
        connection.execute(
            "ALTER TABLE products ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )


def _seed_default_banks(connection: sqlite3.Connection) -> None:
    """Seed rekening default jika tabel banks masih kosong (one-time)."""
    count = connection.execute("SELECT COUNT(*) FROM banks").fetchone()[0]
    if count > 0:
        return
    connection.executemany(
        """
        INSERT INTO banks (bank_name, account_number, account_holder, notes, is_active)
        VALUES (?, ?, ?, ?, 1)
        """,
        [
            ("BCA", "1234567890", "Ucok Store", ""),
            ("GoPay/OVO", "0812-3456-7890", "Ucok Store", "E-Wallet"),
        ],
    )


# ── User ──────────────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str | None, full_name: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            (user_id, username, full_name),
        )
        connection.execute(
            """
            INSERT INTO wallets (user_id, balance)
            VALUES (?, 0)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )


def get_user_profile(user_id: int) -> UserProfile | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT u.user_id, u.username, u.full_name, COALESCE(w.balance, 0)
            FROM users u
            LEFT JOIN wallets w ON w.user_id = u.user_id
            WHERE u.user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if row is None:
        return None
    return UserProfile(
        user_id=row[0],
        username=row[1],
        full_name=row[2],
        balance=row[3],
    )


def get_all_users() -> list[int]:
    """Ambil semua user_id yang pernah menggunakan bot."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT user_id FROM users ORDER BY user_id"
        ).fetchall()
    return [row[0] for row in rows]


# ── Wallet & Transaksi ────────────────────────────────────────────────────────

def update_balance(
    user_id: int,
    amount_delta: int,
    description: str,
    transaction_type: str = "adjustment",
) -> int:
    """
    Update saldo user secara atomic.
    Mencegah saldo negatif untuk transaksi pembelian (transaction_type='purchase').
    Return saldo baru.
    Raise ValueError jika saldo tidak cukup.
    """
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO wallets (user_id, balance)
            VALUES (?, 0)
            ON CONFLICT(user_id) DO NOTHING
            """,
            (user_id,),
        )

        if amount_delta < 0:
            # Cek saldo dulu — atomic dengan SELECT + UPDATE dalam satu transaksi
            current = connection.execute(
                "SELECT balance FROM wallets WHERE user_id = ?", (user_id,)
            ).fetchone()
            if current is None or current[0] + amount_delta < 0:
                raise ValueError(
                    f"Saldo tidak cukup. Saldo: {current[0] if current else 0}, "
                    f"dibutuhkan: {abs(amount_delta)}"
                )

        connection.execute(
            """
            UPDATE wallets
            SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (amount_delta, user_id),
        )
        connection.execute(
            """
            INSERT INTO transactions (user_id, description, transaction_type, amount)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, description, transaction_type, amount_delta),
        )
        new_balance = connection.execute(
            "SELECT balance FROM wallets WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
    return new_balance


def get_user_transactions(user_id: int, limit: int = 10) -> list[TransactionRecord]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, description, transaction_type, amount, created_at
            FROM transactions
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [
        TransactionRecord(
            transaction_id=row[0],
            description=row[1] or "-",
            transaction_type=row[2],
            amount=row[3],
            created_at=row[4],
        )
        for row in rows
    ]


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_bot_stats() -> BotStats:
    with get_connection() as connection:
        total_users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_transactions = connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        total_revenue = connection.execute(
            "SELECT COALESCE(SUM(ABS(amount)), 0) FROM transactions WHERE transaction_type = 'purchase'"
        ).fetchone()[0]
    return BotStats(
        total_users=total_users,
        total_transactions=total_transactions,
        total_revenue=total_revenue,
    )


def get_top_buyers(limit: int = 5) -> list[TopBuyerRecord]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT u.user_id, u.full_name, u.username,
                   COALESCE(SUM(CASE WHEN t.transaction_type = 'purchase' THEN ABS(t.amount) ELSE 0 END), 0) AS total_spent,
                   COUNT(CASE WHEN t.transaction_type = 'purchase' THEN 1 END) AS total_purchases
            FROM users u
            LEFT JOIN transactions t ON t.user_id = u.user_id
            GROUP BY u.user_id
            HAVING total_purchases > 0
            ORDER BY total_spent DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        TopBuyerRecord(
            rank=idx + 1,
            full_name=row[1],
            username=row[2],
            total_spent=row[3],
            total_purchases=row[4],
        )
        for idx, row in enumerate(rows)
    ]


# ── Produk ────────────────────────────────────────────────────────────────────

def create_product(name: str, category: str, price: int, description: str) -> Product:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO products (name, category, price, description, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (name.strip(), category, price, description.strip()),
        )
        product_id = cursor.lastrowid
    return Product(
        product_id=product_id,
        name=name.strip(),
        category=category,
        price=price,
        description=description.strip(),
        is_active=True,
    )


def get_product(product_id: int) -> Product | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, name, category, price, description, is_active
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()
    if row is None:
        return None
    return Product(
        product_id=row[0],
        name=row[1],
        category=row[2],
        price=row[3],
        description=row[4],
        is_active=bool(row[5]),
    )


def get_product_summary(product_id: int) -> ProductSummary | None:
    """Seperti get_product tapi include available_stock."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT p.id, p.name, p.category, p.price, p.description,
                   COUNT(CASE WHEN s.status = 'available' THEN 1 END) AS available_stock
            FROM products p
            LEFT JOIN product_stock s ON s.product_id = p.id
            WHERE p.id = ? AND p.is_active = 1
            GROUP BY p.id
            """,
            (product_id,),
        ).fetchone()
    if row is None:
        return None
    return ProductSummary(
        product_id=row[0],
        name=row[1],
        category=row[2],
        price=row[3],
        description=row[4],
        available_stock=row[5],
    )


def deactivate_product(product_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE products SET is_active = 0 WHERE id = ? AND is_active = 1",
            (product_id,),
        )
    return cursor.rowcount > 0


def list_products(category: str | None = None) -> list[ProductSummary]:
    query = """
        SELECT p.id, p.name, p.category, p.price, p.description,
               COUNT(CASE WHEN s.status = 'available' THEN 1 END) AS available_stock
        FROM products p
        LEFT JOIN product_stock s ON s.product_id = p.id
        WHERE p.is_active = 1
    """
    params: list[object] = []
    if category is not None:
        query += " AND p.category = ?"
        params.append(category)
    query += """
        GROUP BY p.id, p.name, p.category, p.price, p.description
        ORDER BY p.id ASC
    """
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        ProductSummary(
            product_id=row[0],
            name=row[1],
            category=row[2],
            price=row[3],
            description=row[4],
            available_stock=row[5],
        )
        for row in rows
    ]


def add_stock_items(product_id: int, items: list[str]) -> int:
    cleaned_items = [item.strip() for item in items if item.strip()]
    if not cleaned_items:
        return 0
    with get_connection() as connection:
        before = connection.total_changes
        connection.executemany(
            """
            INSERT OR IGNORE INTO product_stock (product_id, content, status)
            VALUES (?, ?, 'available')
            """,
            [(product_id, item) for item in cleaned_items],
        )
        inserted = connection.total_changes - before
    return inserted


def deliver_stock_item(product_id: int, user_id: int) -> str | None:
    """Ambil 1 item stok available dan tandai sebagai delivered. Return konten item atau None."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, content FROM product_stock
            WHERE product_id = ? AND status = 'available'
            ORDER BY id ASC
            LIMIT 1
            """,
            (product_id,),
        ).fetchone()
        if row is None:
            return None
        stock_id, content = row
        connection.execute(
            """
            UPDATE product_stock
            SET status = 'delivered', delivered_to_user_id = ?, delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (user_id, stock_id),
        )
    return content


def get_stock_count(product_id: int) -> int:
    """Hitung stok tersedia untuk satu produk."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM product_stock WHERE product_id = ? AND status = 'available'",
            (product_id,),
        ).fetchone()
    return row[0] if row else 0


def get_low_stock_products(threshold: int = LOW_STOCK_THRESHOLD) -> list[ProductSummary]:
    """Ambil produk otomatis yang stoknya <= threshold."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT p.id, p.name, p.category, p.price, p.description,
                   COUNT(CASE WHEN s.status = 'available' THEN 1 END) AS available_stock
            FROM products p
            LEFT JOIN product_stock s ON s.product_id = p.id
            WHERE p.is_active = 1 AND p.category = 'otomatis'
            GROUP BY p.id
            HAVING available_stock <= ?
            ORDER BY available_stock ASC
            """,
            (threshold,),
        ).fetchall()
    return [
        ProductSummary(
            product_id=row[0],
            name=row[1],
            category=row[2],
            price=row[3],
            description=row[4],
            available_stock=row[5],
        )
        for row in rows
    ]


# ── Pending Checkout (konfirmasi pembelian) ───────────────────────────────────

def set_pending_checkout(user_id: int, product_id: int) -> None:
    """Simpan checkout yang menunggu konfirmasi user."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO pending_checkouts (user_id, product_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                product_id = excluded.product_id,
                created_at = CURRENT_TIMESTAMP
            """,
            (user_id, product_id),
        )


def get_pending_checkout(user_id: int) -> int | None:
    """Ambil product_id dari pending checkout user. None jika tidak ada."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT product_id FROM pending_checkouts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row[0] if row else None


def clear_pending_checkout(user_id: int) -> None:
    """Hapus pending checkout user."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM pending_checkouts WHERE user_id = ?",
            (user_id,),
        )


# ── Admin Log ─────────────────────────────────────────────────────────────────

def add_admin_log(admin_id: int, admin_name: str, action: str, detail: str = "") -> None:
    """Catat aktivitas admin."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO admin_logs (admin_id, admin_name, action, detail)
            VALUES (?, ?, ?, ?)
            """,
            (admin_id, admin_name, action, detail),
        )


def get_admin_logs(limit: int = 20) -> list[AdminLog]:
    """Ambil log aktivitas admin terbaru."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, admin_id, admin_name, action, detail, created_at
            FROM admin_logs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [
        AdminLog(
            log_id=row[0],
            admin_id=row[1],
            admin_name=row[2],
            action=row[3],
            detail=row[4],
            created_at=row[5],
        )
        for row in rows
    ]


# ── Top Up ────────────────────────────────────────────────────────────────────

def create_topup_request(user_id: int, amount: int, proof_file_id: str) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO topup_requests (user_id, amount, proof_file_id, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (user_id, amount, proof_file_id),
        )
    return cursor.lastrowid


def get_pending_topup_requests() -> list[TopUpRequest]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT r.id, r.user_id, u.full_name, u.username, r.amount, r.proof_file_id, r.status, r.created_at
            FROM topup_requests r
            LEFT JOIN users u ON u.user_id = r.user_id
            WHERE r.status = 'pending'
            ORDER BY r.created_at ASC
            """,
        ).fetchall()
    return [
        TopUpRequest(
            request_id=row[0],
            user_id=row[1],
            full_name=row[2],
            username=row[3],
            amount=row[4],
            proof_file_id=row[5],
            status=row[6],
            created_at=row[7],
        )
        for row in rows
    ]


def get_topup_request(request_id: int) -> TopUpRequest | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT r.id, r.user_id, COALESCE(u.full_name, 'Unknown'), u.username,
                   r.amount, r.proof_file_id, r.status, r.created_at
            FROM topup_requests r
            LEFT JOIN users u ON u.user_id = r.user_id
            WHERE r.id = ?
            """,
            (request_id,),
        ).fetchone()
    if row is None:
        return None
    return TopUpRequest(
        request_id=row[0],
        user_id=row[1],
        full_name=row[2],
        username=row[3],
        amount=row[4],
        proof_file_id=row[5],
        status=row[6],
        created_at=row[7],
    )


def approve_topup_request(request_id: int, admin_id: int) -> TopUpRequest | None:
    req = get_topup_request(request_id)
    if req is None or req.status != "pending":
        return None
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE topup_requests
            SET status = 'approved', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (admin_id, request_id),
        )
    update_balance(req.user_id, req.amount, f"Top up disetujui admin (req #{request_id})", "topup")
    return req


def reject_topup_request(request_id: int, admin_id: int) -> TopUpRequest | None:
    req = get_topup_request(request_id)
    if req is None or req.status != "pending":
        return None
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE topup_requests
            SET status = 'rejected', reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (admin_id, request_id),
        )
    return req


# ── Edit Produk ───────────────────────────────────────────────────────────────

PRODUCT_EDITABLE_FIELDS = {"name", "category", "price", "description"}


def update_product_field(product_id: int, field: str, value) -> bool:
    """Update satu kolom produk. Return True jika berhasil."""
    if field not in PRODUCT_EDITABLE_FIELDS:
        raise ValueError(f"Field '{field}' tidak boleh di-edit.")
    column_map = {
        "name": "name",
        "category": "category",
        "price": "price",
        "description": "description",
    }
    column = column_map[field]
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE products SET {column} = ? WHERE id = ? AND is_active = 1",
            (value, product_id),
        )
    return cursor.rowcount > 0


# ── Bot Settings (key-value) ──────────────────────────────────────────────────

def set_setting(key: str, value: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO bot_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
            """,
            (key, value),
        )


def get_setting(key: str, default: str = "") -> str:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (key,),
        ).fetchone()
    return row[0] if row else default


def is_maintenance_mode() -> bool:
    return get_setting("maintenance_mode", "off") == "on"


def set_maintenance_mode(active: bool, message: str = "") -> None:
    set_setting("maintenance_mode", "on" if active else "off")
    if active and message.strip():
        set_setting("maintenance_message", message.strip())


def get_maintenance_message() -> str:
    return get_setting(
        "maintenance_message",
        "Bot sedang dalam pemeliharaan. Silakan coba lagi nanti.",
    )


# ── Banks (rekening dinamis) ──────────────────────────────────────────────────

BANK_EDITABLE_FIELDS = {"bank_name", "account_number", "account_holder", "notes"}


def add_bank(bank_name: str, account_number: str, account_holder: str, notes: str = "") -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO banks (bank_name, account_number, account_holder, notes, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (bank_name.strip(), account_number.strip(), account_holder.strip(), notes.strip()),
        )
    return cursor.lastrowid


def list_banks(active_only: bool = False) -> list[Bank]:
    query = "SELECT id, bank_name, account_number, account_holder, notes, is_active FROM banks"
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY is_active DESC, id ASC"
    with get_connection() as connection:
        rows = connection.execute(query).fetchall()
    return [
        Bank(
            bank_id=row[0],
            bank_name=row[1],
            account_number=row[2],
            account_holder=row[3],
            notes=row[4],
            is_active=bool(row[5]),
        )
        for row in rows
    ]


def get_bank(bank_id: int) -> Bank | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, bank_name, account_number, account_holder, notes, is_active FROM banks WHERE id = ?",
            (bank_id,),
        ).fetchone()
    if row is None:
        return None
    return Bank(
        bank_id=row[0],
        bank_name=row[1],
        account_number=row[2],
        account_holder=row[3],
        notes=row[4],
        is_active=bool(row[5]),
    )


def update_bank_field(bank_id: int, field: str, value: str) -> bool:
    if field not in BANK_EDITABLE_FIELDS:
        raise ValueError(f"Field '{field}' tidak boleh di-edit.")
    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE banks SET {field} = ? WHERE id = ?",
            (value.strip(), bank_id),
        )
    return cursor.rowcount > 0


def toggle_bank_active(bank_id: int) -> Bank | None:
    """Toggle status active. Return Bank baru atau None jika tidak ditemukan."""
    bank = get_bank(bank_id)
    if bank is None:
        return None
    new_status = 0 if bank.is_active else 1
    with get_connection() as connection:
        connection.execute(
            "UPDATE banks SET is_active = ? WHERE id = ?", (new_status, bank_id),
        )
    return get_bank(bank_id)


def delete_bank(bank_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM banks WHERE id = ?", (bank_id,),
        )
    return cursor.rowcount > 0


# ── Daily Login Bonus ─────────────────────────────────────────────────────────

def _calc_bonus_amount(streak: int) -> int:
    """Hitung jumlah bonus berdasarkan streak. Cap di DAILY_BONUS_MAX_STREAK."""
    effective = min(streak, DAILY_BONUS_MAX_STREAK)
    return DAILY_BONUS_BASE + DAILY_BONUS_STEP * (effective - 1)


def get_daily_bonus_status(user_id: int) -> DailyBonusInfo:
    """Cek status klaim hari ini tanpa benar-benar klaim."""
    today = date.today().isoformat()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT last_claim_date, streak FROM daily_bonus_claims WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    profile = get_user_profile(user_id)
    balance = profile.balance if profile else 0
    if row is None:
        # Belum pernah klaim — tampilkan reward hari pertama
        return DailyBonusInfo(
            success=False,
            already_claimed=False,
            claimed_amount=0,
            streak=0,
            next_amount=_calc_bonus_amount(1),
            new_balance=balance,
            next_claim_at="sekarang",
        )
    last_date_str, streak = row
    if last_date_str == today:
        return DailyBonusInfo(
            success=False,
            already_claimed=True,
            claimed_amount=0,
            streak=streak,
            next_amount=_calc_bonus_amount(_next_streak(last_date_str, streak)),
            new_balance=balance,
            next_claim_at="besok",
        )
    # Belum klaim hari ini
    next_streak = _next_streak(last_date_str, streak)
    return DailyBonusInfo(
        success=False,
        already_claimed=False,
        claimed_amount=0,
        streak=streak,
        next_amount=_calc_bonus_amount(next_streak),
        new_balance=balance,
        next_claim_at="sekarang",
    )


def _next_streak(last_date_str: str, current_streak: int) -> int:
    """Tentukan streak baru jika klaim hari ini."""
    try:
        last = date.fromisoformat(last_date_str)
    except (ValueError, TypeError):
        return 1
    today = date.today()
    delta = (today - last).days
    if delta <= 0:
        return current_streak  # masih hari yang sama (atau aneh)
    if delta == 1:
        return current_streak + 1
    return 1  # gap > 1 hari → reset


def claim_daily_bonus(user_id: int) -> DailyBonusInfo:
    """Klaim bonus harian. Idempotent untuk hari yang sama."""
    today = date.today().isoformat()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT last_claim_date, streak, total_claimed FROM daily_bonus_claims WHERE user_id = ?",
            (user_id,),
        ).fetchone()

    if row is not None and row[0] == today:
        # Sudah klaim hari ini
        profile = get_user_profile(user_id)
        balance = profile.balance if profile else 0
        return DailyBonusInfo(
            success=False,
            already_claimed=True,
            claimed_amount=0,
            streak=row[1],
            next_amount=_calc_bonus_amount(_next_streak(row[0], row[1])),
            new_balance=balance,
            next_claim_at="besok",
        )

    if row is None:
        new_streak = 1
        prev_total = 0
    else:
        new_streak = _next_streak(row[0], row[1])
        prev_total = row[2]

    bonus_amount = _calc_bonus_amount(new_streak)

    # Tambah saldo user (transaction_type='bonus' agar tidak masuk omzet)
    new_balance = update_balance(
        user_id,
        bonus_amount,
        f"Bonus harian (streak hari ke-{new_streak})",
        "bonus",
    )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO daily_bonus_claims (user_id, last_claim_date, streak, total_claimed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_claim_date = excluded.last_claim_date,
                streak = excluded.streak,
                total_claimed = daily_bonus_claims.total_claimed + ?
            """,
            (user_id, today, new_streak, prev_total + bonus_amount, bonus_amount),
        )

    return DailyBonusInfo(
        success=True,
        already_claimed=False,
        claimed_amount=bonus_amount,
        streak=new_streak,
        next_amount=_calc_bonus_amount(min(new_streak + 1, DAILY_BONUS_MAX_STREAK)),
        new_balance=new_balance,
        next_claim_at="besok",
    )
