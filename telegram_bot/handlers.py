from __future__ import annotations

import asyncio
import functools
import re
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from telegram_bot.product_browser import (
    CB_BACK,
    CB_BUY,
    CB_DETAIL,
    CB_PAGE,
    ITEMS_PER_PAGE,
    _detail_keyboard,
    _page_keyboard,
    build_catalog_caption,
    build_detail_caption,
)
from telegram_bot.admin_utils import (
    parse_bank_field_value,
    parse_bank_input,
    parse_maintenance_command,
    parse_product_field_value,
    parse_product_input,
    parse_stock_caption,
    parse_topup_caption,
)
from telegram_bot.messages import (
    MENU_ADMIN_ADD_PRODUCT,
    MENU_ADMIN_BANKS,
    MENU_ADMIN_BACK,
    MENU_ADMIN_DEL_PRODUCT,
    MENU_ADMIN_EDIT_PRODUCT,
    MENU_ADMIN_LIST_PRODUCTS,
    MENU_ADMIN_LOGS,
    MENU_ADMIN_TOPUP_REQUESTS,
    MENU_ADMIN_UPLOAD_STOCK,
    MENU_AUTO_PRODUCTS,
    MENU_BACK,
    MENU_BANK_ADD,
    MENU_BANK_BACK,
    MENU_BANK_DELETE,
    MENU_BANK_EDIT,
    MENU_BANK_TOGGLE,
    MENU_DAILY_BONUS,
    MENU_HISTORY,
    MENU_MANUAL_PRODUCTS,
    MENU_PRODUCTS,
    MENU_SALDO_BACK,
    MENU_TOP_BUYER,
    MENU_TOPUP,
    MENU_TOPUP_MANUAL,
    MENU_TOPUP_QRIS,
    StartProfile,
    admin_bank_add_message,
    admin_bank_delete_message,
    admin_bank_edit_field_prompt,
    admin_bank_edit_id_message,
    admin_bank_edit_value_prompt,
    admin_bank_menu_message,
    admin_bank_toggle_message,
    admin_del_product_message,
    admin_edit_field_prompt_message,
    admin_edit_product_detail_message,
    admin_edit_select_id_message,
    admin_edit_success_message,
    admin_product_input_message,
    admin_upload_stock_message,
    admin_welcome_message,
    balance_menu_label,
    checkout_confirm_message,
    daily_bonus_already_claimed_message,
    daily_bonus_overview_message,
    daily_bonus_success_message,
    format_admin_logs,
    format_bank_list_admin,
    format_product_list,
    format_rupiah,
    format_top_buyers,
    format_topup_requests,
    format_transaction_history,
    format_user_product_list,
    help_message,
    low_stock_alert_message,
    maintenance_active_message,
    maintenance_help_message,
    maintenance_status_message,
    menu_message,
    ping_message,
    start_message,
    topup_guide_message,
    topup_qris_message,
    saldo_menu_message,
    invoice_message,
    payment_loading_steps,
)
from telegram_bot.stats import (
    LOW_STOCK_THRESHOLD,
    add_admin_log,
    add_stock_items,
    add_bank,
    approve_topup_request,
    claim_daily_bonus,
    clear_pending_checkout,
    create_product,
    create_topup_request,
    deactivate_product,
    delete_bank,
    deliver_stock_item,
    get_admin_logs,
    get_all_users,
    get_bank,
    get_bot_stats,
    get_daily_bonus_status,
    get_maintenance_message,
    get_low_stock_products,
    get_pending_checkout,
    get_pending_topup_requests,
    get_product,
    get_product_summary,
    get_stock_count,
    get_top_buyers,
    get_user_profile,
    get_user_transactions,
    is_maintenance_mode,
    list_banks,
    list_products,
    reject_topup_request,
    set_maintenance_mode,
    set_pending_checkout,
    toggle_bank_active,
    update_bank_field,
    update_product_field,
    update_balance,
    upsert_user,
)

import math as _math

# ── State keys ────────────────────────────────────────────────────────────────

ADMIN_STATE_KEY = "admin_state"
ADMIN_STATE_ADD_PRODUCT = "add_product"
ADMIN_STATE_UPLOAD_STOCK = "upload_stock"
ADMIN_STATE_DEL_PRODUCT = "del_product"
ADMIN_STATE_BROADCAST = "broadcast"
ADMIN_STATE_EDIT_PRODUCT_ID = "edit_product_id"
ADMIN_STATE_EDIT_PRODUCT_VALUE = "edit_product_value"
ADMIN_STATE_BANK_MENU = "bank_menu"
ADMIN_STATE_BANK_ADD = "bank_add"
ADMIN_STATE_BANK_EDIT_ID = "bank_edit_id"
ADMIN_STATE_BANK_EDIT_VALUE = "bank_edit_value"
ADMIN_STATE_BANK_TOGGLE = "bank_toggle"
ADMIN_STATE_BANK_DELETE = "bank_delete"

USER_STATE_KEY = "user_state"
USER_STATE_TOPUP = "topup"
USER_STATE_CONFIRM_BUY = "confirm_buy"
CATALOG_MSG_KEY = "catalog_message_id"
EDIT_PRODUCT_DATA_KEY = "edit_product_data"
EDIT_BANK_DATA_KEY = "edit_bank_data"

# Checkout expiry (10 menit)
CHECKOUT_EXPIRY_MINUTES = 10


# ── Keyboard builders ─────────────────────────────────────────────────────────

def _build_main_keyboard(balance: int, bonus_claimed: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [balance_menu_label(balance)],
        [MENU_PRODUCTS, MENU_HISTORY],
    ]
    if not bonus_claimed:
        rows.append([MENU_DAILY_BONUS])
    return ReplyKeyboardMarkup(
        rows,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _build_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [MENU_ADMIN_ADD_PRODUCT, MENU_ADMIN_UPLOAD_STOCK],
            [MENU_ADMIN_LIST_PRODUCTS, MENU_ADMIN_EDIT_PRODUCT],
            [MENU_ADMIN_DEL_PRODUCT, MENU_ADMIN_BANKS],
            [MENU_ADMIN_TOPUP_REQUESTS, MENU_ADMIN_LOGS],
            [MENU_ADMIN_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _build_saldo_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard sub-menu Saldo: Top Up Manual, Top Up Otomatis (QRIS), Kembali."""
    return ReplyKeyboardMarkup(
        [
            [MENU_TOPUP_MANUAL],
            [MENU_TOPUP_QRIS],
            [MENU_SALDO_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _build_admin_bank_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [MENU_BANK_ADD, MENU_BANK_EDIT],
            [MENU_BANK_TOGGLE, MENU_BANK_DELETE],
            [MENU_BANK_BACK],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _build_products_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[MENU_AUTO_PRODUCTS], [MENU_MANUAL_PRODUCTS], [MENU_BACK]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _build_confirm_keyboard() -> InlineKeyboardMarkup:
    """Keyboard konfirmasi pembelian: Bayar / Batal."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Ya, Bayar Sekarang", callback_data="checkout_confirm"),
            InlineKeyboardButton("❌ Batal", callback_data="checkout_cancel"),
        ]
    ])


def _build_soldout_keyboard() -> InlineKeyboardMarkup:
    """Keyboard tombol Beli yang di-disable saat stok habis."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Stok Habis", callback_data="soldout_noop")],
    ])


def _build_edit_product_field_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard: pilih field produk untuk di-edit."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Nama", callback_data=f"editprod_field:{product_id}:name"),
            InlineKeyboardButton("📂 Kategori", callback_data=f"editprod_field:{product_id}:category"),
        ],
        [
            InlineKeyboardButton("💵 Harga", callback_data=f"editprod_field:{product_id}:price"),
            InlineKeyboardButton("📝 Deskripsi", callback_data=f"editprod_field:{product_id}:description"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="editprod_cancel")],
    ])


def _build_edit_bank_field_keyboard(bank_id: int) -> InlineKeyboardMarkup:
    """Inline keyboard: pilih field bank untuk di-edit."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏦 Nama Bank", callback_data=f"editbank_field:{bank_id}:bank_name"),
            InlineKeyboardButton("🔢 No.Rekening", callback_data=f"editbank_field:{bank_id}:account_number"),
        ],
        [
            InlineKeyboardButton("👤 Atas Nama", callback_data=f"editbank_field:{bank_id}:account_holder"),
            InlineKeyboardButton("📝 Catatan", callback_data=f"editbank_field:{bank_id}:notes"),
        ],
        [InlineKeyboardButton("❌ Batal", callback_data="editbank_cancel")],
    ])


def _build_daily_bonus_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard: tombol klaim bonus harian."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Klaim Bonus Sekarang", callback_data="bonus_claim")],
    ])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user is None:
        return False
    settings = context.application.bot_data["settings"]
    return user.id in settings.admin_ids


def _admin_name(update: Update) -> str:
    user = update.effective_user
    return user.full_name if user else "Admin"


def maintenance_guard(handler):
    """Decorator: block handler jika maintenance mode aktif (kecuali admin).

    Admin tetap bisa pakai semua fitur saat maintenance mode aktif.
    User non-admin akan menerima pesan maintenance.
    """
    @functools.wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if is_maintenance_mode() and not _is_admin(update, context):
            custom = get_maintenance_message()
            text = maintenance_active_message(custom)
            # CallbackQuery: jawab dengan alert, jangan kirim pesan baru
            if update.callback_query is not None:
                try:
                    await update.callback_query.answer(
                        "🛠️ Bot sedang maintenance. Coba lagi nanti.",
                        show_alert=True,
                    )
                except Exception:
                    pass
                return
            if update.effective_message is not None:
                try:
                    await update.effective_message.reply_text(text, parse_mode="HTML")
                except Exception:
                    pass
            return
        return await handler(update, context)
    return wrapper


async def _notify_low_stock(context: ContextTypes.DEFAULT_TYPE, product_id: int, product_name: str) -> None:
    """Kirim notifikasi ke semua admin jika stok produk menipis/habis."""
    stock = get_stock_count(product_id)
    if stock > LOW_STOCK_THRESHOLD:
        return
    settings = context.application.bot_data["settings"]
    alert = low_stock_alert_message(product_name, product_id, stock)
    for admin_id in settings.admin_ids:
        try:
            await context.bot.send_message(chat_id=admin_id, text=alert, parse_mode="HTML")
        except Exception:
            pass


def _is_checkout_expired(created_at_str: str) -> bool:
    """Cek apakah pending checkout sudah kadaluarsa (> CHECKOUT_EXPIRY_MINUTES menit)."""
    try:
        created_at = datetime.fromisoformat(created_at_str)
        return datetime.utcnow() - created_at > timedelta(minutes=CHECKOUT_EXPIRY_MINUTES)
    except Exception:
        return True


# ── Product catalog ───────────────────────────────────────────────────────────

async def _send_product_catalog(
    update,
    context,
    category: str,
    page: int,
    edit: bool = False,
) -> None:
    products = list_products(category)
    total_pages = max(1, _math.ceil(len(products) / ITEMS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))

    caption = build_catalog_caption(products, page, category, total_pages)
    keyboard = _page_keyboard(products, page, category)
    settings = context.application.bot_data["settings"]

    if edit:
        query = update.callback_query
        if query and query.message:
            try:
                if query.message.photo:
                    await query.message.edit_caption(caption=caption, parse_mode="HTML", reply_markup=keyboard)
                else:
                    await query.message.edit_text(text=caption, parse_mode="HTML", reply_markup=keyboard)
            except Exception:
                pass
        return

    existing_msg_id = context.user_data.get(CATALOG_MSG_KEY)
    chat_id = update.effective_chat.id if update.effective_chat else None

    if existing_msg_id and chat_id:
        try:
            if settings.banner_path.exists():
                await context.bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=existing_msg_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            else:
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=existing_msg_id,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
            return
        except Exception:
            context.user_data[CATALOG_MSG_KEY] = None

    message = update.effective_message
    if message is None:
        return

    if settings.banner_path.exists():
        with settings.banner_path.open("rb") as banner:
            sent = await message.reply_photo(
                photo=banner,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
    else:
        sent = await message.reply_text(caption, parse_mode="HTML", reply_markup=keyboard)

    context.user_data[CATALOG_MSG_KEY] = sent.message_id


@maintenance_guard
async def product_callback_handler(update, context) -> None:
    """Handle semua callback dari inline keyboard katalog produk + checkout."""
    query = update.callback_query
    if query is None:
        return

    data = query.data or ""

    # ── Noop: tombol disabled (sold out) ─────────────────────────────────────
    if data == "soldout_noop":
        await query.answer("🚫 Stok produk ini sedang habis.", show_alert=True)
        return

    # ── Daily Bonus: klaim ───────────────────────────────────────────────────
    if data == "bonus_claim":
        user = update.effective_user
        if user is None:
            return
        upsert_user(
            user.id,
            user.username,
            user.full_name.strip() or user.first_name or "Teman",
        )
        info = claim_daily_bonus(user.id)
        if info.already_claimed:
            await query.answer("⏰ Sudah klaim hari ini!", show_alert=True)
            text = daily_bonus_already_claimed_message(info)
        else:
            await query.answer(f"+{format_rupiah(info.claimed_amount)} 🎉")
            text = daily_bonus_success_message(info)
        try:
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=None)
            elif query.message:
                await query.message.edit_text(text=text, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        # Refresh main keyboard (saldo bisa berubah)
        if info.success:
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"Saldo kamu sekarang: <b>{format_rupiah(info.new_balance)}</b>",
                    parse_mode="HTML",
                    reply_markup=_build_main_keyboard(info.new_balance, bonus_claimed=True),
                )
            except Exception:
                pass
        return

    # ── Edit Produk: admin pilih field via inline button ─────────────────────
    if data.startswith("editprod_field:"):
        if not _is_admin(update, context):
            await query.answer("Bukan admin.", show_alert=True)
            return
        parts = data.split(":")
        if len(parts) != 3:
            await query.answer("Format callback salah.", show_alert=True)
            return
        try:
            product_id = int(parts[1])
        except ValueError:
            await query.answer("ID produk invalid.", show_alert=True)
            return
        field = parts[2]
        product = get_product(product_id)
        if product is None:
            await query.answer("Produk tidak ditemukan.", show_alert=True)
            return
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_EDIT_PRODUCT_VALUE
        context.user_data[EDIT_PRODUCT_DATA_KEY] = {"product_id": product_id, "field": field}
        await query.answer()
        prompt = admin_edit_field_prompt_message(product, field)
        try:
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=prompt, parse_mode="HTML", reply_markup=None)
            elif query.message:
                await query.message.edit_text(text=prompt, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    if data == "editprod_cancel":
        if not _is_admin(update, context):
            await query.answer("Bukan admin.", show_alert=True)
            return
        context.user_data[ADMIN_STATE_KEY] = None
        context.user_data.pop(EDIT_PRODUCT_DATA_KEY, None)
        await query.answer("Edit dibatalkan.")
        try:
            cancel_msg = "❌ <b>Edit produk dibatalkan.</b>"
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=cancel_msg, parse_mode="HTML", reply_markup=None)
            elif query.message:
                await query.message.edit_text(text=cancel_msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    # ── Edit Bank: admin pilih field via inline button ───────────────────────
    if data.startswith("editbank_field:"):
        if not _is_admin(update, context):
            await query.answer("Bukan admin.", show_alert=True)
            return
        parts = data.split(":")
        if len(parts) != 3:
            await query.answer("Format callback salah.", show_alert=True)
            return
        try:
            bank_id = int(parts[1])
        except ValueError:
            await query.answer("ID bank invalid.", show_alert=True)
            return
        field = parts[2]
        bank = get_bank(bank_id)
        if bank is None:
            await query.answer("Bank tidak ditemukan.", show_alert=True)
            return
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_EDIT_VALUE
        context.user_data[EDIT_BANK_DATA_KEY] = {"bank_id": bank_id, "field": field}
        await query.answer()
        prompt = admin_bank_edit_value_prompt(bank, field)
        try:
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=prompt, parse_mode="HTML", reply_markup=None)
            elif query.message:
                await query.message.edit_text(text=prompt, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    if data == "editbank_cancel":
        if not _is_admin(update, context):
            await query.answer("Bukan admin.", show_alert=True)
            return
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
        context.user_data.pop(EDIT_BANK_DATA_KEY, None)
        await query.answer("Edit dibatalkan.")
        try:
            cancel_msg = "❌ <b>Edit bank dibatalkan.</b>"
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=cancel_msg, parse_mode="HTML", reply_markup=None)
            elif query.message:
                await query.message.edit_text(text=cancel_msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    # ── Konfirmasi checkout ──────────────────────────────────────────────────
    if data == "checkout_confirm":
        # Jawab query DULU sebelum proses — hindari "query expired"
        await query.answer()
        await _process_confirmed_purchase(update, context, query)
        return

    if data == "checkout_cancel":
        user = update.effective_user
        if user:
            clear_pending_checkout(user.id)
            context.user_data[USER_STATE_KEY] = None
        profile = get_user_profile(user.id) if user else None
        bal = profile.balance if profile else 0

        # FIX: gunakan edit_caption untuk pesan foto, edit_text untuk teks biasa
        try:
            if query.message and query.message.photo:
                await query.message.edit_caption(
                    caption="❌ <b>Pembelian dibatalkan.</b>\n\nKamu bisa memilih produk lain.",
                    parse_mode="HTML",
                    reply_markup=None,
                )
            elif query.message:
                await query.message.edit_text(
                    "❌ <b>Pembelian dibatalkan.</b>\n\nKamu bisa memilih produk lain.",
                    parse_mode="HTML",
                    reply_markup=None,
                )
        except Exception:
            pass
        await query.answer("Pembelian dibatalkan.")
        return

    # Jawab query untuk semua callback lainnya
    await query.answer()

    # ── Navigasi halaman ──────────────────────────────────────────────────────
    if data.startswith(f"{CB_PAGE}:"):
        parts = data.split(":")
        category = parts[1]
        page = int(parts[2])
        await _send_product_catalog(update, context, category, page, edit=True)
        return

    if data.startswith(f"{CB_BACK}:"):
        parts = data.split(":")
        category = parts[1]
        page = int(parts[2])
        await _send_product_catalog(update, context, category, page, edit=True)
        return

    # ── Detail produk ─────────────────────────────────────────────────────────
    if data.startswith(f"{CB_DETAIL}:"):
        parts = data.split(":")
        product_id = int(parts[1])
        page = int(parts[2])
        category = parts[3]

        product = get_product_summary(product_id)
        if product is None:
            await query.answer("Produk tidak ditemukan.", show_alert=True)
            return

        user = update.effective_user
        profile = get_user_profile(user.id) if user else None
        balance = profile.balance if profile else 0

        detail_caption = build_detail_caption(product, balance)

        # FIX: auto-disable tombol Beli jika stok habis (produk otomatis)
        if product.available_stock == 0 and product.category == "otomatis":
            keyboard = _detail_keyboard_soldout(product_id, page, category)
        else:
            keyboard = _detail_keyboard(product_id, page, category)

        try:
            if query.message and query.message.photo:
                await query.message.edit_caption(
                    caption=detail_caption, parse_mode="HTML", reply_markup=keyboard
                )
            elif query.message:
                await query.message.edit_text(
                    text=detail_caption, parse_mode="HTML", reply_markup=keyboard
                )
        except Exception:
            pass
        return

    # ── Tombol Beli → validasi realtime + tampilkan konfirmasi ───────────────
    if data.startswith(f"{CB_BUY}:"):
        parts = data.split(":")
        product_id = int(parts[1])

        user = update.effective_user
        if user is None:
            return

        # Re-fetch data terbaru (realtime check)
        product = get_product_summary(product_id)
        profile = get_user_profile(user.id)

        if product is None:
            await query.answer("❌ Produk tidak tersedia.", show_alert=True)
            return
        if profile is None:
            return

        # FIX: cek stok SEBELUM query.answer() agar show_alert bisa muncul
        if product.available_stock == 0 and product.category == "otomatis":
            await query.answer("🚫 Stok habis! Silakan hubungi admin untuk restock.", show_alert=True)
            # Auto-update tombol jadi disabled
            try:
                user_p = get_user_profile(user.id)
                bal = user_p.balance if user_p else 0
                detail_caption = build_detail_caption(product, bal)
                keyboard = _detail_keyboard_soldout(product_id, 0, product.category)
                if query.message and query.message.photo:
                    await query.message.edit_caption(
                        caption=detail_caption, parse_mode="HTML", reply_markup=keyboard
                    )
                elif query.message:
                    await query.message.edit_text(
                        text=detail_caption, parse_mode="HTML", reply_markup=keyboard
                    )
            except Exception:
                pass
            return

        if profile.balance < product.price:
            kekurangan = product.price - profile.balance
            await query.answer(
                f"❌ Saldo tidak cukup!\nKurang: {format_rupiah(kekurangan)}",
                show_alert=True,
            )
            return

        # Simpan pending checkout → tampilkan konfirmasi
        set_pending_checkout(user.id, product_id)
        context.user_data[USER_STATE_KEY] = USER_STATE_CONFIRM_BUY

        confirm_text = checkout_confirm_message(
            product.name, product.price, profile.balance, product.category
        )
        try:
            if query.message and query.message.photo:
                await query.message.edit_caption(
                    caption=confirm_text,
                    parse_mode="HTML",
                    reply_markup=_build_confirm_keyboard(),
                )
            elif query.message:
                await query.message.edit_text(
                    text=confirm_text,
                    parse_mode="HTML",
                    reply_markup=_build_confirm_keyboard(),
                )
        except Exception:
            pass
        return


def _detail_keyboard_soldout(product_id: int, page: int, category: str) -> InlineKeyboardMarkup:
    """Keyboard detail produk saat stok habis — tombol Beli di-disable."""
    from telegram_bot.product_browser import encode, CB_BACK
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚫 Stok Habis — Tidak Tersedia", callback_data="soldout_noop")],
        [InlineKeyboardButton("← Kembali ke Daftar", callback_data=encode(CB_BACK, category, page))],
    ])


async def _process_confirmed_purchase(update, context, query) -> None:
    """Eksekusi pembelian setelah user konfirmasi — dengan animasi loading."""
    user = update.effective_user
    if user is None:
        return

    product_id = get_pending_checkout(user.id)
    if product_id is None:
        try:
            msg = (
                "⚠️ <b>Sesi checkout kadaluarsa.</b>\n\n"
                f"Sesi pembelian hanya berlaku {CHECKOUT_EXPIRY_MINUTES} menit.\n"
                "Silakan ulangi dari daftar produk."
            )
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=msg, parse_mode="HTML", reply_markup=None)
            else:
                await query.message.edit_text(msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    clear_pending_checkout(user.id)
    context.user_data[USER_STATE_KEY] = None

    product = get_product_summary(product_id)
    profile = get_user_profile(user.id)

    if product is None or profile is None:
        try:
            msg = "❌ Produk tidak ditemukan."
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=msg, parse_mode="HTML", reply_markup=None)
            else:
                await query.message.edit_text(msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    # Re-validasi saldo
    if profile.balance < product.price:
        try:
            msg = (
                f"❌ <b>Saldo tidak cukup.</b>\n\n"
                f"Saldo kamu : {format_rupiah(profile.balance)}\n"
                f"Harga      : {format_rupiah(product.price)}\n\n"
                f"Top up dulu melalui menu <b>Top Up Saldo</b>."
            )
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=msg, parse_mode="HTML", reply_markup=None)
            else:
                await query.message.edit_text(msg, parse_mode="HTML", reply_markup=None)
        except Exception:
            pass
        return

    # ── Animasi loading payment ───────────────────────────────────────────────
    async def _set_caption(text: str, markup=None):
        try:
            if query.message and query.message.photo:
                await query.message.edit_caption(caption=text, parse_mode="HTML", reply_markup=markup)
            elif query.message:
                await query.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        except Exception:
            pass

    steps = payment_loading_steps(product.name, product.price)
    for step_text in steps:
        await _set_caption(step_text)
        await asyncio.sleep(0.8)

    # ── Proses pembelian ──────────────────────────────────────────────────────
    if product.category == "otomatis":
        if product.available_stock == 0:
            await _set_caption(
                "⚠️ <b>Stok habis saat dikonfirmasi.</b>\n\nHubungi admin untuk restock."
            )
            return

        item_content = deliver_stock_item(product_id, user.id)
        if item_content is None:
            await _set_caption("⚠️ <b>Stok habis.</b> Hubungi admin.")
            return

        try:
            new_balance = update_balance(user.id, -product.price, f"Beli {product.name}", "purchase")
        except ValueError as e:
            await _set_caption(f"❌ {e}")
            return

        profile_updated = get_user_profile(user.id)
        bal = profile_updated.balance if profile_updated else new_balance

        # Invoice modern
        invoice_text = invoice_message(
            product_name=product.name,
            price=product.price,
            item_content=item_content,
            remaining_balance=bal,
            user_id=user.id,
            username=user.username,
        )
        await _set_caption(invoice_text)

        # Notifikasi stok menipis ke admin (async)
        asyncio.create_task(_notify_low_stock(context, product_id, product.name))

    else:
        # Manual product
        try:
            new_balance = update_balance(
                user.id, -product.price, f"Beli {product.name} (manual)", "purchase"
            )
        except ValueError as e:
            await _set_caption(f"❌ {e}")
            return

        profile_updated = get_user_profile(user.id)
        bal = profile_updated.balance if profile_updated else new_balance
        uname = f"@{user.username}" if user.username else user.full_name

        invoice_text = invoice_message(
            product_name=product.name,
            price=product.price,
            item_content=None,
            remaining_balance=bal,
            user_id=user.id,
            username=user.username,
            is_manual=True,
        )
        await _set_caption(invoice_text)

        settings = context.application.bot_data["settings"]
        for admin_id in settings.admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🛒 <b>Pesanan Masuk!</b>\n"
                        f"{'─' * 20}\n"
                        f"👤 User    : {uname} (UID: <code>{user.id}</code>)\n"
                        f"📦 Produk  : {product.name} (ID: {product_id})\n"
                        f"💵 Harga   : {format_rupiah(product.price)}"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

    # Kirim ulang keyboard utama dengan saldo terbaru
    try:
        await context.bot.send_message(
            chat_id=user.id,
            text="Kamu bisa lanjut belanja atau kembali ke menu utama.",
            reply_markup=_build_main_keyboard(bal),
        )
    except Exception:
        pass


# ── Render home ───────────────────────────────────────────────────────────────

async def render_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if message is None or user is None:
        return
    context.user_data[CATALOG_MSG_KEY] = None
    clear_pending_checkout(user.id)

    upsert_user(user.id, user.username, user.full_name.strip() or user.first_name or "Teman")
    profile = get_user_profile(user.id)
    if profile is None:
        return

    stats = get_bot_stats()
    caption = start_message(
        StartProfile(
            full_name=profile.full_name,
            username=profile.username,
            user_id=profile.user_id,
            balance=profile.balance,
            total_users=stats.total_users,
            total_transactions=stats.total_transactions,
            current_time=datetime.now(),
        )
    )
    bonus_info = get_daily_bonus_status(user.id)
    keyboard = _build_main_keyboard(profile.balance, bonus_claimed=bonus_info.already_claimed)
    settings = context.application.bot_data["settings"]

    if settings.banner_path.exists():
        with settings.banner_path.open("rb") as banner_file:
            await message.reply_photo(photo=banner_file, caption=caption, reply_markup=keyboard, parse_mode="HTML")
        return

    await message.reply_text(caption, reply_markup=keyboard, parse_mode="HTML")


# ── Command handlers ──────────────────────────────────────────────────────────

@maintenance_guard
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await render_home(update, context)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(help_message(), parse_mode="HTML")


async def ping_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    message = update.effective_message
    if message is None:
        return
    await message.reply_text(ping_message(), parse_mode="HTML")


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if not _is_admin(update, context):
        await message.reply_text("Kamu tidak punya akses admin.")
        return
    context.user_data[ADMIN_STATE_KEY] = None
    await message.reply_text(admin_welcome_message(), reply_markup=_build_admin_keyboard())


async def approve_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or message.text is None:
        return
    if not _is_admin(update, context):
        await message.reply_text("Kamu tidak punya akses admin.")
        return
    match = re.match(r"^/approve_(\d+)$", message.text.strip())
    if not match:
        await message.reply_text("Format salah. Gunakan: /approve_<id>")
        return
    request_id = int(match.group(1))
    admin_user = update.effective_user
    if admin_user is None:
        return
    req = approve_topup_request(request_id, admin_user.id)
    if req is None:
        await message.reply_text(f"Permintaan #{request_id} tidak ditemukan atau sudah diproses.")
        return

    add_admin_log(
        admin_user.id, admin_user.full_name,
        "APPROVE TOPUP",
        f"req #{request_id} | user {req.user_id} | {format_rupiah(req.amount)}"
    )

    await message.reply_text(
        f"✅ Top up #{request_id} disetujui.\n"
        f"User: {req.full_name} (UID: {req.user_id})\n"
        f"Jumlah: {format_rupiah(req.amount)}"
    )
    try:
        profile = get_user_profile(req.user_id)
        new_balance = profile.balance if profile else 0
        await context.bot.send_message(
            chat_id=req.user_id,
            text=(
                f"✅ <b>Top Up Berhasil!</b>\n\n"
                f"💰 Jumlah    : {format_rupiah(req.amount)}\n"
                f"💳 Saldo baru: {format_rupiah(new_balance)}\n\n"
                f"Terima kasih sudah top up! Selamat belanja 🛒"
            ),
            parse_mode="HTML",
            reply_markup=_build_main_keyboard(new_balance),
        )
    except Exception:
        pass


async def reject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or message.text is None:
        return
    if not _is_admin(update, context):
        await message.reply_text("Kamu tidak punya akses admin.")
        return
    match = re.match(r"^/reject_(\d+)$", message.text.strip())
    if not match:
        await message.reply_text("Format salah. Gunakan: /reject_<id>")
        return
    request_id = int(match.group(1))
    admin_user = update.effective_user
    if admin_user is None:
        return
    req = reject_topup_request(request_id, admin_user.id)
    if req is None:
        await message.reply_text(f"Permintaan #{request_id} tidak ditemukan atau sudah diproses.")
        return

    add_admin_log(
        admin_user.id, admin_user.full_name,
        "REJECT TOPUP",
        f"req #{request_id} | user {req.user_id} | {format_rupiah(req.amount)}"
    )

    await message.reply_text(
        f"❌ Top up #{request_id} ditolak.\n"
        f"User: {req.full_name} (UID: {req.user_id})\n"
        f"Jumlah: {format_rupiah(req.amount)}"
    )
    try:
        await context.bot.send_message(
            chat_id=req.user_id,
            text=(
                f"❌ <b>Top Up Ditolak</b>\n\n"
                f"Permintaan top up sebesar {format_rupiah(req.amount)} ditolak oleh admin.\n\n"
                f"Hubungi admin jika ada pertanyaan."
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    if not _is_admin(update, context):
        await message.reply_text("Kamu tidak punya akses admin.")
        return

    context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BROADCAST
    await message.reply_text(
        "📢 Mode Broadcast Aktif\n\n"
        "Kirim pesan yang ingin di-broadcast ke semua user.\n"
        "Bisa berupa:\n"
        "• Teks (support HTML format)\n"
        "• Foto dengan caption\n"
        "• Dokumen dengan caption\n\n"
        "Kirim /cancel untuk membatalkan."
    )


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return

    admin_state = context.user_data.get(ADMIN_STATE_KEY)
    user_state = context.user_data.get(USER_STATE_KEY)
    user = update.effective_user

    if admin_state is not None and _is_admin(update, context):
        context.user_data[ADMIN_STATE_KEY] = None
        context.user_data.pop(EDIT_PRODUCT_DATA_KEY, None)
        context.user_data.pop(EDIT_BANK_DATA_KEY, None)
        await message.reply_text("❌ Operasi dibatalkan.", reply_markup=_build_admin_keyboard())
    elif user_state is not None:
        context.user_data[USER_STATE_KEY] = None
        if user:
            clear_pending_checkout(user.id)
        profile = get_user_profile(user.id) if user else None
        bal = profile.balance if profile else 0
        await message.reply_text("❌ Operasi dibatalkan.", reply_markup=_build_main_keyboard(bal))
    else:
        await message.reply_text("Tidak ada operasi yang perlu dibatalkan.")


async def stats_handler(update, context) -> None:
    message = update.effective_message
    if message is None:
        return
    if not _is_admin(update, context):
        await message.reply_text("Kamu tidak punya akses admin.")
        return

    stats = get_bot_stats()
    products = list_products()
    requests = get_pending_topup_requests()
    top_buyers = get_top_buyers(3)
    low_stock = get_low_stock_products()

    total_stock = sum(p.available_stock for p in products)
    auto_products = sum(1 for p in products if p.category == "otomatis")
    manual_products = sum(1 for p in products if p.category == "manual")

    top_str = ""
    if top_buyers:
        medals = ["🥇", "🥈", "🥉"]
        for i, b in enumerate(top_buyers):
            uname = f"@{b.username}" if b.username else b.full_name
            top_str += f"\n{medals[i]} {uname} — {format_rupiah(b.total_spent)}"
    else:
        top_str = "\n(belum ada)"

    low_stock_str = ""
    if low_stock:
        low_stock_str = "\n\n⚠️ Stok Menipis:\n"
        for p in low_stock:
            stok_label = "HABIS" if p.available_stock == 0 else f"{p.available_stock} tersisa"
            low_stock_str += f"  • {p.name} [{stok_label}]\n"

    await message.reply_text(
        f"📊 Statistik Bot\n"
        f"{'─' * 22}\n"
        f"👥 Total user    : {stats.total_users}\n"
        f"💳 Transaksi     : {stats.total_transactions}\n"
        f"💰 Total omzet   : {format_rupiah(stats.total_revenue)}\n"
        f"📦 Produk aktif  : {len(products)} ({auto_products} otomatis, {manual_products} manual)\n"
        f"🗄️ Total stok    : {total_stock} item\n"
        f"⏳ Topup pending : {len(requests)}"
        f"{low_stock_str}\n\n"
        f"🏆 Top 3 Buyer:{top_str}",
        reply_markup=_build_admin_keyboard(),
    )


async def myid_handler(update, context) -> None:
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    await message.reply_text(
        f"🪪 Info Akun Kamu\n"
        f"ID       : <code>{user.id}</code>\n"
        f"Username : @{user.username or '-'}\n"
        f"Nama     : {user.full_name}",
        parse_mode="HTML",
    )


async def addbalance_handler(update, context) -> None:
    message = update.effective_message
    if message is None:
        return
    if not _is_admin(update, context):
        await message.reply_text("Kamu tidak punya akses admin.")
        return

    args = context.args or []
    if len(args) != 2 or not args[0].isdigit() or not args[1].lstrip("-").isdigit():
        await message.reply_text(
            "Format: /addbal <user_id> <jumlah>\n"
            "Contoh tambah: /addbal 123456789 50000\n"
            "Contoh kurang: /addbal 123456789 -10000"
        )
        return

    target_id = int(args[0])
    amount = int(args[1])
    profile = get_user_profile(target_id)
    if profile is None:
        await message.reply_text(f"User ID {target_id} tidak ditemukan.")
        return

    admin_user = update.effective_user
    admin_name = admin_user.full_name if admin_user else "Admin"
    try:
        new_bal = update_balance(target_id, amount, f"Adjustment oleh {admin_name}", "adjustment")
    except ValueError as e:
        await message.reply_text(f"❌ Gagal: {e}")
        return

    sign = "+" if amount >= 0 else ""
    add_admin_log(
        admin_user.id if admin_user else 0,
        admin_name,
        "ADJUST BALANCE",
        f"user {target_id} | {sign}{format_rupiah(amount)} | saldo baru: {format_rupiah(new_bal)}"
    )

    await message.reply_text(
        f"✅ Saldo berhasil diubah.\n"
        f"User : {profile.full_name} (UID: {target_id})\n"
        f"Ubah : {sign}{format_rupiah(amount)}\n"
        f"Saldo baru: {format_rupiah(new_bal)}",
        reply_markup=_build_admin_keyboard(),
    )
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                f"{'✅' if amount >= 0 else '⚠️'} Saldo kamu diubah oleh admin.\n"
                f"Perubahan  : {sign}{format_rupiah(amount)}\n"
                f"Saldo baru : {format_rupiah(new_bal)}"
            ),
        )
    except Exception:
        pass


# ── Maintenance handler ──────────────────────────────────────────────────────

async def maintenance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Aktifkan/non-aktifkan maintenance mode.

    Usage:
      /maintenance              → tampilkan status
      /maintenance on <pesan>   → aktifkan dengan pesan custom
      /maintenance off          → nonaktifkan
    """
    message = update.effective_message
    if message is None:
        return
    if not _is_admin(update, context):
        await message.reply_text("Kamu tidak punya akses admin.")
        return

    args = context.args or []
    if not args:
        active = is_maintenance_mode()
        custom = get_maintenance_message() if active else ""
        await message.reply_text(
            maintenance_status_message(active, custom) + "\n\n" + maintenance_help_message(),
            parse_mode="HTML",
        )
        return

    try:
        active, msg = parse_maintenance_command(args)
    except ValueError as exc:
        await message.reply_text(str(exc), parse_mode="HTML")
        return

    set_maintenance_mode(active, msg)
    admin_user = update.effective_user
    add_admin_log(
        admin_user.id if admin_user else 0,
        _admin_name(update),
        "MAINTENANCE ON" if active else "MAINTENANCE OFF",
        msg or "-",
    )
    await message.reply_text(
        maintenance_status_message(active, msg),
        parse_mode="HTML",
    )


# ── Daily Bonus handler ──────────────────────────────────────────────────────

@maintenance_guard
async def daily_bonus_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tampilkan overview bonus harian + tombol klaim (jika belum klaim)."""
    del context
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return
    upsert_user(
        user.id,
        user.username,
        user.full_name.strip() or user.first_name or "Teman",
    )
    info = get_daily_bonus_status(user.id)
    if info.already_claimed:
        await message.reply_text(
            daily_bonus_overview_message(info),
            parse_mode="HTML",
        )
    else:
        await message.reply_text(
            daily_bonus_overview_message(info),
            parse_mode="HTML",
            reply_markup=_build_daily_bonus_keyboard(),
        )


# ── Admin menu handlers ───────────────────────────────────────────────────────

async def _handle_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """Return True jika pesan ditangani sebagai menu admin, False jika tidak."""
    message = update.effective_message
    if message is None:
        return False

    admin_state = context.user_data.get(ADMIN_STATE_KEY)

    ADMIN_MENU_BUTTONS = {
        MENU_ADMIN_ADD_PRODUCT, MENU_ADMIN_UPLOAD_STOCK, MENU_ADMIN_LIST_PRODUCTS,
        MENU_ADMIN_DEL_PRODUCT, MENU_ADMIN_EDIT_PRODUCT, MENU_ADMIN_BANKS,
        MENU_ADMIN_TOPUP_REQUESTS, MENU_ADMIN_BACK, MENU_ADMIN_LOGS,
    }
    BANK_SUBMENU_BUTTONS = {
        MENU_BANK_ADD, MENU_BANK_EDIT, MENU_BANK_TOGGLE,
        MENU_BANK_DELETE, MENU_BANK_BACK,
    }
    ALL_ADMIN_BUTTONS = ADMIN_MENU_BUTTONS | BANK_SUBMENU_BUTTONS

    # Broadcast teks
    if admin_state == ADMIN_STATE_BROADCAST and text not in ALL_ADMIN_BUTTONS:
        await _do_broadcast_text(update, context, text)
        return True

    # Input tambah produk
    if admin_state == ADMIN_STATE_ADD_PRODUCT and text not in ALL_ADMIN_BUTTONS:
        try:
            draft = parse_product_input(text)
        except ValueError as exc:
            await message.reply_text(str(exc), reply_markup=_build_admin_keyboard())
            return True
        product = create_product(draft.name, draft.category, draft.price, draft.description)
        context.user_data[ADMIN_STATE_KEY] = None
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "TAMBAH PRODUK",
            f"ID {product.product_id} | {product.name} | {format_rupiah(product.price)}"
        )
        await message.reply_text(
            f"✅ Produk berhasil ditambahkan.\nID: {product.product_id} | Nama: {product.name}",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    # Input hapus produk
    if admin_state == ADMIN_STATE_DEL_PRODUCT and text not in ALL_ADMIN_BUTTONS:
        if not text.strip().isdigit():
            await message.reply_text("ID produk harus berupa angka.", reply_markup=_build_admin_keyboard())
            return True
        product_id = int(text.strip())
        product = get_product(product_id)
        success = deactivate_product(product_id)
        context.user_data[ADMIN_STATE_KEY] = None
        if success:
            admin_user = update.effective_user
            add_admin_log(
                admin_user.id if admin_user else 0,
                _admin_name(update),
                "HAPUS PRODUK",
                f"ID {product_id}" + (f" | {product.name}" if product else "")
            )
            await message.reply_text(
                f"✅ Produk ID {product_id} berhasil dinonaktifkan.",
                reply_markup=_build_admin_keyboard(),
            )
        else:
            await message.reply_text(
                f"Produk ID {product_id} tidak ditemukan atau sudah tidak aktif.",
                reply_markup=_build_admin_keyboard(),
            )
        return True

    # ── v7: Input Edit Produk — STEP 1: terima ID, tampilkan field selector ─
    if admin_state == ADMIN_STATE_EDIT_PRODUCT_ID and text not in ALL_ADMIN_BUTTONS:
        if not text.strip().isdigit():
            await message.reply_text(
                "ID produk harus berupa angka. Contoh: <code>3</code>",
                parse_mode="HTML",
                reply_markup=_build_admin_keyboard(),
            )
            return True
        product_id = int(text.strip())
        product = get_product(product_id)
        if product is None or not product.is_active:
            await message.reply_text(
                f"Produk ID {product_id} tidak ditemukan atau sudah tidak aktif.",
                reply_markup=_build_admin_keyboard(),
            )
            context.user_data[ADMIN_STATE_KEY] = None
            return True
        # Reset state — sekarang nunggu user klik inline button
        context.user_data[ADMIN_STATE_KEY] = None
        context.user_data[EDIT_PRODUCT_DATA_KEY] = {"product_id": product_id}
        await message.reply_text(
            admin_edit_product_detail_message(product),
            parse_mode="HTML",
            reply_markup=_build_edit_product_field_keyboard(product_id),
        )
        return True

    # ── v7: Input Edit Produk — STEP 2: terima nilai baru ───────────────────
    if admin_state == ADMIN_STATE_EDIT_PRODUCT_VALUE and text not in ALL_ADMIN_BUTTONS:
        edit_data = context.user_data.get(EDIT_PRODUCT_DATA_KEY) or {}
        product_id = edit_data.get("product_id")
        field = edit_data.get("field")
        if not product_id or not field:
            await message.reply_text(
                "Sesi edit hilang. Silakan klik <b>Edit Produk</b> lagi.",
                parse_mode="HTML",
                reply_markup=_build_admin_keyboard(),
            )
            context.user_data[ADMIN_STATE_KEY] = None
            return True
        try:
            new_value = parse_product_field_value(field, text)
        except ValueError as exc:
            await message.reply_text(f"❌ {exc}\n\nCoba lagi atau ketik /cancel.")
            return True
        success = update_product_field(product_id, field, new_value)
        product = get_product(product_id)
        context.user_data[ADMIN_STATE_KEY] = None
        context.user_data.pop(EDIT_PRODUCT_DATA_KEY, None)
        if not success or product is None:
            await message.reply_text(
                f"❌ Gagal update produk ID {product_id}.",
                reply_markup=_build_admin_keyboard(),
            )
            return True
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "EDIT PRODUK",
            f"ID {product_id} | field {field} → {new_value}",
        )
        await message.reply_text(
            admin_edit_success_message(product, field, new_value),
            parse_mode="HTML",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    # ── v7: Bank — Input Tambah Bank ────────────────────────────────────────
    if admin_state == ADMIN_STATE_BANK_ADD and text not in ALL_ADMIN_BUTTONS:
        try:
            draft = parse_bank_input(text)
        except ValueError as exc:
            await message.reply_text(str(exc), reply_markup=_build_admin_bank_keyboard())
            return True
        bank_id = add_bank(draft.bank_name, draft.account_number, draft.account_holder, draft.notes)
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "TAMBAH BANK",
            f"ID {bank_id} | {draft.bank_name} | {draft.account_number}",
        )
        banks = list_banks(active_only=False)
        await message.reply_text(
            f"✅ Bank #{bank_id} ({draft.bank_name}) berhasil ditambahkan.\n\n"
            f"{format_bank_list_admin(banks)}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    # ── v7: Bank — Input ID untuk Edit Bank ─────────────────────────────────
    if admin_state == ADMIN_STATE_BANK_EDIT_ID and text not in ALL_ADMIN_BUTTONS:
        if not text.strip().isdigit():
            await message.reply_text(
                "ID bank harus berupa angka.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        bank_id = int(text.strip())
        bank = get_bank(bank_id)
        if bank is None:
            await message.reply_text(
                f"Bank ID {bank_id} tidak ditemukan.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
            return True
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
        context.user_data[EDIT_BANK_DATA_KEY] = {"bank_id": bank_id}
        await message.reply_text(
            admin_bank_edit_field_prompt(bank),
            parse_mode="HTML",
            reply_markup=_build_edit_bank_field_keyboard(bank_id),
        )
        return True

    # ── v7: Bank — Input nilai baru untuk field bank ────────────────────────
    if admin_state == ADMIN_STATE_BANK_EDIT_VALUE and text not in ALL_ADMIN_BUTTONS:
        edit_data = context.user_data.get(EDIT_BANK_DATA_KEY) or {}
        bank_id = edit_data.get("bank_id")
        field = edit_data.get("field")
        if not bank_id or not field:
            await message.reply_text(
                "Sesi edit bank hilang. Silakan ulangi dari menu.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
            return True
        try:
            new_value = parse_bank_field_value(field, text)
        except ValueError as exc:
            await message.reply_text(f"❌ {exc}\n\nCoba lagi atau ketik /cancel.")
            return True
        success = update_bank_field(bank_id, field, new_value)
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
        context.user_data.pop(EDIT_BANK_DATA_KEY, None)
        if not success:
            await message.reply_text(
                f"❌ Gagal update bank ID {bank_id}.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "EDIT BANK",
            f"ID {bank_id} | field {field} → {new_value}",
        )
        banks = list_banks(active_only=False)
        await message.reply_text(
            f"✅ Bank #{bank_id} field <b>{field}</b> diperbarui.\n\n"
            f"{format_bank_list_admin(banks)}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    # ── v7: Bank — Toggle aktif/non-aktif ───────────────────────────────────
    if admin_state == ADMIN_STATE_BANK_TOGGLE and text not in ALL_ADMIN_BUTTONS:
        if not text.strip().isdigit():
            await message.reply_text(
                "ID bank harus berupa angka.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        bank_id = int(text.strip())
        bank = toggle_bank_active(bank_id)
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
        if bank is None:
            await message.reply_text(
                f"Bank ID {bank_id} tidak ditemukan.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        admin_user = update.effective_user
        new_status = "AKTIF" if bank.is_active else "NONAKTIF"
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "TOGGLE BANK",
            f"ID {bank_id} | {bank.bank_name} → {new_status}",
        )
        banks = list_banks(active_only=False)
        status_icon = "🟢" if bank.is_active else "🔴"
        await message.reply_text(
            f"{status_icon} Bank #{bank_id} ({bank.bank_name}) → <b>{new_status}</b>\n\n"
            f"{format_bank_list_admin(banks)}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    # ── v7: Bank — Hapus permanen ───────────────────────────────────────────
    if admin_state == ADMIN_STATE_BANK_DELETE and text not in ALL_ADMIN_BUTTONS:
        if not text.strip().isdigit():
            await message.reply_text(
                "ID bank harus berupa angka.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        bank_id = int(text.strip())
        bank = get_bank(bank_id)
        if bank is None:
            await message.reply_text(
                f"Bank ID {bank_id} tidak ditemukan.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
            return True
        success = delete_bank(bank_id)
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
        if not success:
            await message.reply_text(
                f"❌ Gagal hapus bank ID {bank_id}.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "HAPUS BANK",
            f"ID {bank_id} | {bank.bank_name}",
        )
        banks = list_banks(active_only=False)
        await message.reply_text(
            f"🗑️ Bank #{bank_id} ({bank.bank_name}) telah dihapus.\n\n"
            f"{format_bank_list_admin(banks)}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    # Tombol menu admin
    if text == MENU_ADMIN_ADD_PRODUCT:
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_ADD_PRODUCT
        await message.reply_text(admin_product_input_message(), reply_markup=_build_admin_keyboard())
        return True

    if text == MENU_ADMIN_UPLOAD_STOCK:
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_UPLOAD_STOCK
        products = list_products()
        await message.reply_text(
            f"{format_product_list(products)}\n\n{admin_upload_stock_message()}",
            parse_mode="HTML",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    if text == MENU_ADMIN_LIST_PRODUCTS:
        await message.reply_text(
            format_product_list(list_products()),
            parse_mode="HTML",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    if text == MENU_ADMIN_EDIT_PRODUCT:
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_EDIT_PRODUCT_ID
        products = list_products()
        await message.reply_text(
            f"{format_product_list(products)}\n\n{admin_edit_select_id_message()}",
            parse_mode="HTML",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    if text == MENU_ADMIN_DEL_PRODUCT:
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_DEL_PRODUCT
        products = list_products()
        await message.reply_text(
            f"{format_product_list(products)}\n\n{admin_del_product_message()}",
            parse_mode="HTML",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    if text == MENU_ADMIN_BANKS:
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_MENU
        banks = list_banks(active_only=False)
        await message.reply_text(
            f"{format_bank_list_admin(banks)}\n\n{admin_bank_menu_message()}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    # ── Bank sub-menu buttons ───────────────────────────────────────────────
    if text == MENU_BANK_ADD:
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_ADD
        await message.reply_text(
            admin_bank_add_message(),
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    if text == MENU_BANK_EDIT:
        banks = list_banks(active_only=False)
        if not banks:
            await message.reply_text(
                "Belum ada bank yang bisa di-edit. Tambah dulu lewat ➕ Tambah Bank.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_EDIT_ID
        await message.reply_text(
            f"{format_bank_list_admin(banks)}\n\n{admin_bank_edit_id_message()}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    if text == MENU_BANK_TOGGLE:
        banks = list_banks(active_only=False)
        if not banks:
            await message.reply_text(
                "Belum ada bank. Tambah dulu lewat ➕ Tambah Bank.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_TOGGLE
        await message.reply_text(
            f"{format_bank_list_admin(banks)}\n\n{admin_bank_toggle_message()}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    if text == MENU_BANK_DELETE:
        banks = list_banks(active_only=False)
        if not banks:
            await message.reply_text(
                "Belum ada bank yang bisa dihapus.",
                reply_markup=_build_admin_bank_keyboard(),
            )
            return True
        context.user_data[ADMIN_STATE_KEY] = ADMIN_STATE_BANK_DELETE
        await message.reply_text(
            f"{format_bank_list_admin(banks)}\n\n{admin_bank_delete_message()}",
            parse_mode="HTML",
            reply_markup=_build_admin_bank_keyboard(),
        )
        return True

    if text == MENU_BANK_BACK:
        context.user_data[ADMIN_STATE_KEY] = None
        context.user_data.pop(EDIT_BANK_DATA_KEY, None)
        await message.reply_text(
            "Kembali ke menu admin.",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    if text == MENU_ADMIN_TOPUP_REQUESTS:
        requests = get_pending_topup_requests()
        await message.reply_text(
            format_topup_requests(requests),
            parse_mode="HTML",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    if text == MENU_ADMIN_LOGS:
        logs = get_admin_logs(20)
        await message.reply_text(
            format_admin_logs(logs),
            parse_mode="HTML",
            reply_markup=_build_admin_keyboard(),
        )
        return True

    if text == MENU_ADMIN_BACK:
        context.user_data[ADMIN_STATE_KEY] = None
        await render_home(update, context)
        return True

    return False


async def _do_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Broadcast teks ke semua user."""
    message = update.effective_message
    if message is None:
        return

    all_users = get_all_users()
    total = len(all_users)
    progress_msg = await message.reply_text(f"📤 Mengirim broadcast ke {total} user...")

    success = 0
    failed = 0
    for user_id in all_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    context.user_data[ADMIN_STATE_KEY] = None
    admin_user = update.effective_user
    add_admin_log(
        admin_user.id if admin_user else 0,
        _admin_name(update),
        "BROADCAST TEKS",
        f"berhasil: {success}/{total}"
    )
    await progress_msg.edit_text(
        f"✅ Broadcast selesai!\n\nTotal user: {total}\n✅ Berhasil: {success}\n❌ Gagal: {failed}"
    )
    await message.reply_text("Kembali ke menu admin.", reply_markup=_build_admin_keyboard())


# ── User menu handlers ────────────────────────────────────────────────────────

async def _handle_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    """Return True jika pesan ditangani sebagai menu user."""
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return False

    # Beli produk (ketik "beli <id>")
    buy_match = re.match(r"^beli\s+(\d+)$", text.strip(), re.IGNORECASE)
    if buy_match:
        await _handle_text_buy(update, context, int(buy_match.group(1)))
        return True

    if text == MENU_PRODUCTS:
        await message.reply_text(menu_message(text), reply_markup=_build_products_keyboard())
        return True

    if text == MENU_BACK:
        await render_home(update, context)
        return True

    if text in {MENU_AUTO_PRODUCTS, MENU_MANUAL_PRODUCTS}:
        category = "otomatis" if text == MENU_AUTO_PRODUCTS else "manual"
        await _send_product_catalog(update, context, category, page=0, edit=False)
        return True

    if text == MENU_HISTORY:
        profile = get_user_profile(user.id)
        bal = profile.balance if profile else 0
        transactions = get_user_transactions(user.id, limit=10)
        await message.reply_text(
            format_transaction_history(transactions),
            parse_mode="HTML",
            reply_markup=_build_main_keyboard(bal),
        )
        return True

    if text == MENU_TOP_BUYER:
        profile = get_user_profile(user.id)
        bal = profile.balance if profile else 0
        buyers = get_top_buyers(5)
        await message.reply_text(
            format_top_buyers(buyers),
            parse_mode="HTML",
            reply_markup=_build_main_keyboard(bal),
        )
        return True

    if text == MENU_DAILY_BONUS:
        upsert_user(
            user.id,
            user.username,
            user.full_name.strip() or user.first_name or "Teman",
        )
        info = get_daily_bonus_status(user.id)
        if info.already_claimed:
            profile = get_user_profile(user.id)
            bal = profile.balance if profile else 0
            await message.reply_text(
                daily_bonus_overview_message(info),
                parse_mode="HTML",
                reply_markup=_build_main_keyboard(bal, bonus_claimed=True),
            )
        else:
            await message.reply_text(
                daily_bonus_overview_message(info),
                parse_mode="HTML",
                reply_markup=_build_daily_bonus_keyboard(),
            )
        return True

    if text == MENU_TOPUP or text.startswith("Saldo: "):
        profile = get_user_profile(user.id)
        bal = profile.balance if profile else 0
        await message.reply_text(
            saldo_menu_message(bal),
            parse_mode="HTML",
            reply_markup=_build_saldo_keyboard(),
        )
        return True

    if text == MENU_TOPUP_MANUAL:
        profile = get_user_profile(user.id)
        bal = profile.balance if profile else 0
        context.user_data[USER_STATE_KEY] = USER_STATE_TOPUP
        active_banks = list_banks(active_only=True)
        await message.reply_text(
            topup_guide_message(active_banks),
            parse_mode="HTML",
            reply_markup=_build_saldo_keyboard(),
        )
        return True

    if text == MENU_TOPUP_QRIS:
        await message.reply_text(
            topup_qris_message(),
            parse_mode="HTML",
            reply_markup=_build_saldo_keyboard(),
        )
        return True

    if text == MENU_SALDO_BACK:
        bonus_info = get_daily_bonus_status(user.id)
        profile = get_user_profile(user.id)
        bal = profile.balance if profile else 0
        context.user_data[USER_STATE_KEY] = None
        await message.reply_text(
            "Kembali ke menu utama.",
            reply_markup=_build_main_keyboard(bal, bonus_claimed=bonus_info.already_claimed),
        )
        return True

    if text.strip().lower().startswith("topup"):
        profile = get_user_profile(user.id)
        bal = profile.balance if profile else 0
        await message.reply_text(
            "⚠️ Top up harus disertai bukti transfer (foto atau file)!\n\n"
            "Cara kirim bukti:\n"
            "1. Klik ikon 📎 (lampiran)\n"
            "2. Pilih foto atau file bukti transfer\n"
            "3. Isi caption dengan: topup <jumlah>\n"
            "   Contoh: topup 50000\n\n"
            "Jangan kirim teks saja.",
            reply_markup=_build_main_keyboard(bal),
        )
        return True

    return False


async def _handle_text_buy(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int) -> None:
    """Handle beli <id> — tampilkan konfirmasi sebelum bayar."""
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    product = get_product(product_id)
    profile = get_user_profile(user.id)

    if product is None or not product.is_active:
        await message.reply_text("❌ Produk tidak ditemukan.")
        return
    if profile is None:
        return

    # Cek stok realtime untuk produk otomatis
    if product.category == "otomatis":
        stock = get_stock_count(product_id)
        if stock == 0:
            await message.reply_text(
                f"🚫 <b>Stok {product.name} sedang habis.</b>\n\n"
                f"Silakan hubungi admin untuk restock.",
                parse_mode="HTML",
            )
            return

    if profile.balance < product.price:
        kekurangan = product.price - profile.balance
        await message.reply_text(
            f"❌ Saldo tidak cukup.\n"
            f"Harga: {format_rupiah(product.price)}\n"
            f"Saldo kamu: {format_rupiah(profile.balance)}\n"
            f"Kurang: {format_rupiah(kekurangan)}\n\n"
            f"Top up dulu melalui menu Top Up Saldo."
        )
        return

    # Simpan pending checkout & tampilkan konfirmasi
    set_pending_checkout(user.id, product_id)
    context.user_data[USER_STATE_KEY] = USER_STATE_CONFIRM_BUY

    confirm_text = checkout_confirm_message(
        product.name, product.price, profile.balance, product.category
    )
    await message.reply_text(
        confirm_text,
        parse_mode="HTML",
        reply_markup=_build_confirm_keyboard(),
    )


# ── Echo handler (router utama) ───────────────────────────────────────────────

@maintenance_guard
async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or message.text is None:
        return

    text = message.text

    # Admin route dulu
    if _is_admin(update, context):
        handled = await _handle_admin_menu(update, context, text)
        if handled:
            return

    # User route
    handled = await _handle_user_menu(update, context, text)
    if handled:
        return

    # Fallback
    user = update.effective_user
    profile = get_user_profile(user.id) if user else None
    bal = profile.balance if profile else 0
    await message.reply_text(menu_message(text), reply_markup=_build_main_keyboard(bal))


# ── Document handler ──────────────────────────────────────────────────────────

@maintenance_guard
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or message.document is None:
        return

    caption = message.caption or ""

    # Admin broadcast
    if _is_admin(update, context) and context.user_data.get(ADMIN_STATE_KEY) == ADMIN_STATE_BROADCAST:
        if caption.strip().lower() == "/cancel":
            context.user_data[ADMIN_STATE_KEY] = None
            await message.reply_text("❌ Broadcast dibatalkan.", reply_markup=_build_admin_keyboard())
            return

        all_users = get_all_users()
        total = len(all_users)
        success = 0
        failed = 0
        file_id = message.document.file_id
        progress_msg = await message.reply_text(f"📤 Mengirim broadcast dokumen ke {total} user...")

        for user_id in all_users:
            try:
                await context.bot.send_document(
                    chat_id=user_id, document=file_id, caption=caption, parse_mode="HTML"
                )
                success += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)

        context.user_data[ADMIN_STATE_KEY] = None
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "BROADCAST DOKUMEN",
            f"berhasil: {success}/{total}"
        )
        await progress_msg.edit_text(
            f"✅ Broadcast dokumen selesai!\n\nTotal: {total}\n✅ Berhasil: {success}\n❌ Gagal: {failed}"
        )
        await message.reply_text("Kembali ke menu admin.", reply_markup=_build_admin_keyboard())
        return

    # Admin upload stok
    if _is_admin(update, context) and context.user_data.get(ADMIN_STATE_KEY) == ADMIN_STATE_UPLOAD_STOCK:
        try:
            product_id = parse_stock_caption(caption)
        except ValueError as exc:
            await message.reply_text(str(exc), reply_markup=_build_admin_keyboard())
            return

        product = get_product(product_id)
        if product is None:
            await message.reply_text("Produk tidak ditemukan.", reply_markup=_build_admin_keyboard())
            return

        telegram_file = await message.document.get_file()
        content_bytes = await telegram_file.download_as_bytearray()
        try:
            content = bytes(content_bytes).decode("utf-8")
        except UnicodeDecodeError:
            content = bytes(content_bytes).decode("utf-8", errors="ignore")

        lines = [l.strip() for l in content.splitlines() if l.strip()]
        if not lines:
            await message.reply_text("File kosong atau tidak ada item yang valid.", reply_markup=_build_admin_keyboard())
            return

        inserted = add_stock_items(product_id, lines)
        context.user_data[ADMIN_STATE_KEY] = None
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "UPLOAD STOK",
            f"produk ID {product_id} ({product.name}) | +{inserted} item"
        )
        await message.reply_text(
            f"✅ Upload stok selesai untuk produk {product.name}.\nItem baru masuk: {inserted}",
            reply_markup=_build_admin_keyboard(),
        )
        return

    # User top up via dokumen
    if caption.strip().lower().startswith("topup"):
        user = update.effective_user
        if user is None:
            return
        try:
            amount = parse_topup_caption(caption)
        except ValueError as exc:
            await message.reply_text(f"{exc}\n\nKirim ulang file dengan caption yang benar.\nContoh: topup 50000")
            return

        file_id = message.document.file_id
        request_id = create_topup_request(user.id, amount, file_id)
        context.user_data[USER_STATE_KEY] = None

        profile = get_user_profile(user.id)
        bal = profile.balance if profile else 0

        await message.reply_text(
            f"✅ Permintaan top up #{request_id} diterima!\n"
            f"Jumlah: {format_rupiah(amount)}\n\n"
            f"Admin akan memverifikasi dalam waktu dekat.",
            reply_markup=_build_main_keyboard(bal),
        )

        settings = context.application.bot_data["settings"]
        uname = f"@{user.username}" if user.username else user.full_name
        for admin_id in settings.admin_ids:
            if admin_id == user.id:
                continue
            try:
                await context.bot.send_document(
                    chat_id=admin_id,
                    document=file_id,
                    caption=(
                        f"💰 Top Up Masuk!\n"
                        f"Request ID: #{request_id}\n"
                        f"User: {uname} (UID: {user.id})\n"
                        f"Jumlah: {format_rupiah(amount)}\n\n"
                        f"✅ /approve_{request_id}\n"
                        f"❌ /reject_{request_id}"
                    ),
                )
            except Exception:
                pass
        return

    if _is_admin(update, context):
        await message.reply_text(
            "Gunakan menu Upload Stok untuk upload stok produk,\n"
            "atau kirim file dengan caption `topup <jumlah>` untuk top up saldo.",
            reply_markup=_build_admin_keyboard(),
        )


# ── Photo handler ─────────────────────────────────────────────────────────────

@maintenance_guard
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.photo:
        return

    user = update.effective_user
    if user is None:
        return

    # Admin broadcast foto
    if _is_admin(update, context) and context.user_data.get(ADMIN_STATE_KEY) == ADMIN_STATE_BROADCAST:
        caption = message.caption or ""
        if caption.strip().lower() == "/cancel":
            context.user_data[ADMIN_STATE_KEY] = None
            await message.reply_text("❌ Broadcast dibatalkan.", reply_markup=_build_admin_keyboard())
            return

        all_users = get_all_users()
        total = len(all_users)
        success = 0
        failed = 0
        file_id = message.photo[-1].file_id
        progress_msg = await message.reply_text(f"📤 Mengirim broadcast foto ke {total} user...")

        for user_id in all_users:
            try:
                await context.bot.send_photo(
                    chat_id=user_id, photo=file_id, caption=caption, parse_mode="HTML"
                )
                success += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)

        context.user_data[ADMIN_STATE_KEY] = None
        admin_user = update.effective_user
        add_admin_log(
            admin_user.id if admin_user else 0,
            _admin_name(update),
            "BROADCAST FOTO",
            f"berhasil: {success}/{total}"
        )
        await progress_msg.edit_text(
            f"✅ Broadcast foto selesai!\n\nTotal: {total}\n✅ Berhasil: {success}\n❌ Gagal: {failed}"
        )
        await message.reply_text("Kembali ke menu admin.", reply_markup=_build_admin_keyboard())
        return

    # User: foto sebagai bukti top up
    caption = message.caption or ""
    try:
        amount = parse_topup_caption(caption)
    except ValueError as exc:
        await message.reply_text(f"{exc}\n\nKirim ulang foto dengan caption yang benar.\nContoh: topup 50000")
        return

    file_id = message.photo[-1].file_id
    request_id = create_topup_request(user.id, amount, file_id)
    context.user_data[USER_STATE_KEY] = None

    profile = get_user_profile(user.id)
    bal = profile.balance if profile else 0

    await message.reply_text(
        f"✅ Permintaan top up #{request_id} diterima!\n"
        f"Jumlah: {format_rupiah(amount)}\n\n"
        f"Admin akan memverifikasi dalam waktu dekat.",
        reply_markup=_build_main_keyboard(bal),
    )

    settings = context.application.bot_data["settings"]
    uname = f"@{user.username}" if user.username else user.full_name
    for admin_id in settings.admin_ids:
        if admin_id == user.id:
            continue
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=(
                    f"💰 Top Up Masuk!\n"
                    f"Request ID: #{request_id}\n"
                    f"User: {uname} (UID: {user.id})\n"
                    f"Jumlah: {format_rupiah(amount)}\n\n"
                    f"✅ /approve_{request_id}\n"
                    f"❌ /reject_{request_id}"
                ),
            )
        except Exception:
            pass
