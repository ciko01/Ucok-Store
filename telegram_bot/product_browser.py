"""
product_browser.py — Paginated product catalog dengan InlineKeyboard.

Upgrade v6:
  - Auto-disable tombol nomor produk jika stok habis (otomatis)
  - Label stok di katalog lebih informatif
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

ITEMS_PER_PAGE = 9  # 9 produk per halaman, grid 3x3

# ── Callback data prefixes ────────────────────────────────────────────────────
CB_PAGE   = "prod_page"    # prod_page:<category>:<page>
CB_DETAIL = "prod_detail"  # prod_detail:<product_id>:<page>:<category>
CB_BUY    = "prod_buy"     # prod_buy:<product_id>
CB_BACK   = "prod_back"    # prod_back:<category>:<page>

# ── Helpers ───────────────────────────────────────────────────────────────────

def encode(prefix: str, *parts) -> str:
    return f"{prefix}:{':'.join(str(p) for p in parts)}"


def _page_keyboard(products: list, page: int, category: str) -> InlineKeyboardMarkup:
    """Buat keyboard grid angka (3 kolom) + navigasi halaman.
    Tombol produk habis (otomatis) otomatis di-disable dengan tanda 🚫.
    """
    total_pages = max(1, math.ceil(len(products) / ITEMS_PER_PAGE))
    start = page * ITEMS_PER_PAGE
    end   = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    # Grid angka 3 kolom
    num_rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, prod in enumerate(page_products):
        global_num = start + i + 1
        is_soldout = prod.category == "otomatis" and prod.available_stock == 0

        if is_soldout:
            # Tombol disabled — callback noop agar tidak error
            btn = InlineKeyboardButton(
                f"🚫{global_num}",
                callback_data="soldout_noop",
            )
        else:
            btn = InlineKeyboardButton(
                str(global_num),
                callback_data=encode(CB_DETAIL, prod.product_id, page, category),
            )
        row.append(btn)
        if len(row) == 3:
            num_rows.append(row)
            row = []
    if row:
        num_rows.append(row)

    # Navigasi
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            "← Prev",
            callback_data=encode(CB_PAGE, category, page - 1),
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            "Selanjutnya →",
            callback_data=encode(CB_PAGE, category, page + 1),
        ))

    keyboard = num_rows
    if nav:
        keyboard = keyboard + [nav]

    return InlineKeyboardMarkup(keyboard)


def _detail_keyboard(product_id: int, page: int, category: str) -> InlineKeyboardMarkup:
    """Keyboard di halaman detail produk: Beli + Kembali."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Beli Sekarang", callback_data=encode(CB_BUY, product_id))],
        [InlineKeyboardButton("← Kembali ke Daftar", callback_data=encode(CB_BACK, category, page))],
    ])


# ── Caption builders ──────────────────────────────────────────────────────────

def build_catalog_caption(
    products: list,
    page: int,
    category: str,
    total_pages: int,
) -> str:
    start = page * ITEMS_PER_PAGE
    end   = start + ITEMS_PER_PAGE
    page_products = products[start:end]

    cat_label = "Produk Otomatis 🤖" if category == "otomatis" else "Produk Manual 👤"
    lines = [f"📦 <b>Daftar {cat_label}</b>\n"]

    for i, p in enumerate(page_products):
        num = start + i + 1
        is_soldout = p.category == "otomatis" and p.available_stock == 0
        if is_soldout:
            lines.append(f"🚫 {num}. <s>{p.name}</s> — <i>Habis</i>")
        else:
            lines.append(f"✅ {num}. {p.name}")

    lines.append(f"\n📄 Halaman {page + 1}/{total_pages}")
    lines.append("Ketuk nomor untuk detail & beli.")
    if any(p.category == "otomatis" and p.available_stock == 0 for p in page_products):
        lines.append("🚫 = stok habis, tidak bisa dibeli")
    return "\n".join(lines)


def build_detail_caption(product, balance: int) -> str:
    from telegram_bot.messages import format_rupiah
    
    if product.available_stock == 0 and product.category == "otomatis":
        stok_line = "🚫 <b>Stok habis</b>"
    elif product.category == "otomatis":
        stok_line = f"✅ Stok tersedia: <b>{product.available_stock}</b>"
    else:
        stok_line = "📬 Tersedia (pengiriman manual)"

    cat_label = "🤖 Otomatis (langsung kirim)" if product.category == "otomatis" else "👤 Manual (admin kirim)"
    saldo_line = f"💰 Saldo kamu  : {format_rupiah(balance)}"

    kurang = product.price - balance
    if kurang > 0:
        saldo_line += f"\n❌ Kurang       : {format_rupiah(kurang)}"

    return (
        f"🏷️ <b>{product.name}</b>\n"
        f"{'━' * 24}\n"
        f"💵 Harga   : {format_rupiah(product.price)}\n"
        f"📂 Tipe    : {cat_label}\n"
        f"{stok_line}\n\n"
        f"📝 {product.description}\n\n"
        f"{'━' * 24}\n"
        f"{saldo_line}"
    )
