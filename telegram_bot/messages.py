from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MENU_PRODUCTS = "List Produk"
MENU_HISTORY = "Riwayat Transaksi"
MENU_TOP_BUYER = "Top Five Buyer"
MENU_AUTO_PRODUCTS = "Produk Otomatis"
MENU_MANUAL_PRODUCTS = "Produk Manual"
MENU_BACK = "< Back"
MENU_TOPUP = "Top Up Saldo"
MENU_DAILY_BONUS = "🎁 Bonus Harian"
MENU_ADMIN_ADD_PRODUCT = "Tambah Produk"
MENU_ADMIN_UPLOAD_STOCK = "Upload Stok"
MENU_ADMIN_LIST_PRODUCTS = "Lihat Produk"
MENU_ADMIN_EDIT_PRODUCT = "Edit Produk"
MENU_ADMIN_DEL_PRODUCT = "Hapus Produk"
MENU_ADMIN_TOPUP_REQUESTS = "Cek Top Up"
MENU_ADMIN_BACK = "Kembali Home"
MENU_ADMIN_LOGS = "Log Aktivitas"
MENU_ADMIN_BANKS = "Kelola Bank"
MENU_ADMIN_MAINTENANCE = "Maintenance"

# Sub-menu Kelola Bank
MENU_BANK_ADD = "➕ Tambah Bank"
MENU_BANK_EDIT = "✏️ Edit Bank"
MENU_BANK_TOGGLE = "🔄 Aktif/NonAktifkan"
MENU_BANK_DELETE = "🗑️ Hapus Bank"
MENU_BANK_BACK = "← Kembali Admin"


@dataclass(frozen=True)
class StartProfile:
    full_name: str
    username: str | None
    user_id: int
    balance: int
    total_users: int
    total_transactions: int
    current_time: datetime


WEEKDAYS_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
MONTHS_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def format_rupiah(amount: int) -> str:
    return "Rp {:,}".format(amount).replace(",", ".")


def balance_menu_label(balance: int) -> str:
    return f"Saldo: {format_rupiah(balance)}"


def format_indonesian_datetime(value: datetime) -> str:
    weekday = WEEKDAYS_ID[value.weekday()]
    month = MONTHS_ID[value.month - 1]
    return f"{weekday}, {value.day:02d} {month} {value.year} {value:%H:%M}"


def start_message(profile: StartProfile) -> str:
    username_line = f"@{profile.username}" if profile.username else "-"
    return (
        f"╔══════════════════════╗\n"
        f"║   🛒 <b>UCOK STORE</b>         ║\n"
        f"╚══════════════════════╝\n\n"
        f"👋 Halo, <b>{profile.full_name}</b>!\n"
        f"🕐 {format_indonesian_datetime(profile.current_time)}\n\n"
        f"━━━ 👤 <b>Profil Kamu</b> ━━━\n"
        f"🪪 ID        : <code>{profile.user_id}</code>\n"
        f"📛 Username  : {username_line}\n"
        f"💰 Saldo     : <b>{format_rupiah(profile.balance)}</b>\n\n"
        f"━━━ 📊 <b>Statistik Bot</b> ━━━\n"
        f"👥 Total User       : {profile.total_users}\n"
        f"💳 Total Transaksi  : {profile.total_transactions}\n\n"
        f"Pilih menu di bawah untuk mulai belanja! 👇"
    )


def help_message() -> str:
    return (
        "📋 <b>Command yang Tersedia</b>\n\n"
        "/start  — halaman utama\n"
        "/help   — lihat bantuan ini\n"
        "/ping   — cek bot online\n"
        "/myid   — lihat Telegram ID kamu\n"
        "/bonus  — klaim bonus harian\n"
        "/cancel — batalkan operasi aktif\n\n"
        "🔐 <b>Admin Only</b>\n"
        "/admin  — panel admin\n"
        "/bc     — broadcast pesan\n"
        "/stats  — statistik bot\n"
        "/addbal — ubah saldo user\n"
        "/maintenance — mode pemeliharaan\n\n"
        "📦 <b>Menu Utama</b>\n"
        "• <b>List Produk</b> — lihat & beli produk\n"
        "• <b>Riwayat Transaksi</b> — 10 transaksi terakhir\n"
        "• <b>Top Five Buyer</b> — leaderboard pembeli\n"
        "• <b>Top Up Saldo</b> — isi saldo wallet\n"
        "• <b>🎁 Bonus Harian</b> — klaim saldo gratis tiap hari"
    )


def ping_message() -> str:
    return "🟢 <b>Pong!</b> Bot online dan siap melayani."


def echo_message(text: str) -> str:
    clean_text = text.strip()
    if not clean_text:
        return "Saya menerima pesan kosong. Coba kirim teks biasa."
    return f"Kamu bilang: {clean_text}"


def menu_message(menu_text: str) -> str:
    if menu_text == MENU_PRODUCTS:
        return (
            "📦 <b>Pilih Kategori Produk</b>\n\n"
            "Gunakan tombol di bawah untuk memilih\n"
            "<b>Produk Otomatis</b> atau <b>Produk Manual</b>."
        )
    if menu_text == MENU_BACK:
        return "Kembali ke menu utama."
    return echo_message(menu_text)


def admin_welcome_message() -> str:
    return (
        "🔐 <b>Panel Admin Aktif</b>\n\n"
        "Pilih menu di keyboard untuk mengelola\n"
        "produk, stok, dan permintaan top up.\n\n"
        "━━━ Command Admin ━━━\n"
        "/bc — broadcast pesan ke semua user\n"
        "/stats — statistik lengkap\n"
        "/addbal &lt;uid&gt; &lt;jumlah&gt; — ubah saldo user\n"
        "/maintenance on &lt;pesan&gt; | off — mode pemeliharaan\n"
        "/cancel — batalkan operasi aktif"
    )


def admin_product_input_message() -> str:
    return (
        "➕ <b>Tambah Produk Baru</b>\n\n"
        "Kirim dengan format:\n"
        "<code>nama | kategori | harga | deskripsi</code>\n\n"
        "Contoh:\n"
        "<code>Netflix 1P1U | otomatis | 50000 | Akun private 1 profile 1 user</code>\n\n"
        "⚠️ <b>Aturan:</b>\n"
        "• Nama max 100 karakter\n"
        "• Harga minimal Rp 1.000\n"
        "• Kategori: <code>otomatis</code> atau <code>manual</code>"
    )


def admin_upload_stock_message() -> str:
    return (
        "📤 <b>Upload Stok Produk</b>\n\n"
        "Kirim file <code>.txt</code> berisi stok,\n"
        "satu baris = satu item.\n\n"
        "Caption wajib: <code>stok &lt;id_produk&gt;</code>\n"
        "Contoh: <code>stok 1</code>"
    )


def admin_del_product_message() -> str:
    return (
        "🗑️ <b>Hapus Produk</b>\n\n"
        "Kirim <b>ID produk</b> yang ingin dinonaktifkan.\n"
        "Contoh: <code>3</code>\n\n"
        "Produk yang dinonaktifkan tidak akan muncul\n"
        "di daftar user."
    )


def format_product_list(products: list[object]) -> str:
    if not products:
        return "Belum ada produk aktif."
    lines = ["📦 <b>Daftar Produk:</b>"]
    for p in products:
        stok_str = str(p.available_stock) if p.category == "otomatis" else "∞"
        stok_icon = "🔴" if p.category == "otomatis" and p.available_stock == 0 else "🟢"
        lines.append(
            f"{stok_icon} <b>{p.product_id}. {p.name}</b>\n"
            f"   [{p.category}] {format_rupiah(p.price)} | stok: {stok_str}"
        )
    return "\n".join(lines)


def format_user_product_list(title: str, products: list[object]) -> str:
    if not products:
        return f"{title} belum tersedia."
    lines = [title]
    for p in products:
        stok_info = f"Stok: {p.available_stock}" if p.available_stock > 0 else "⚠️ Stok habis"
        lines.append(
            f"\n#{p.product_id} — {p.name}\n"
            f"Harga: {format_rupiah(p.price)}\n"
            f"{stok_info}\n"
            f"{p.description}\n"
            f"👉 Ketik: beli {p.product_id}"
        )
    return "\n".join(lines).strip()


def format_transaction_history(transactions: list[object]) -> str:
    if not transactions:
        return "📭 Riwayat transaksi kamu masih kosong."
    lines = ["📋 <b>Riwayat 10 Transaksi Terakhir</b>\n"]
    for t in transactions:
        sign = "+" if t.amount >= 0 else ""
        tipe_map = {
            "purchase": ("🛒", "Pembelian"),
            "topup":    ("💰", "Top Up"),
            "adjustment": ("⚙️", "Adjustment"),
            "bonus":    ("🎁", "Bonus Harian"),
        }
        icon, label = tipe_map.get(t.transaction_type, ("📄", t.transaction_type))
        amount_str = f"{sign}{format_rupiah(t.amount)}"
        lines.append(
            f"{icon} <b>{label}</b> — {amount_str}\n"
            f"   {t.description}\n"
            f"   🕐 {t.created_at[:16]}"
        )
    return "\n\n".join(lines)


def format_top_buyers(buyers: list[object]) -> str:
    if not buyers:
        return "🏆 Top Five Buyer belum ada data.\nJadi yang pertama beli produk kami! 🛒"
    lines = ["🏆 <b>Top Five Buyer</b> 🏆\n"]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    for b in buyers:
        medal = medals[b.rank - 1] if b.rank <= len(medals) else f"{b.rank}."
        uname = f"@{b.username}" if b.username else b.full_name
        lines.append(
            f"{medal} <b>{uname}</b>\n"
            f"   💰 {format_rupiah(b.total_spent)}  •  🛒 {b.total_purchases}x beli"
        )
    return "\n\n".join(lines)


def topup_guide_message(banks: list[object] | None = None) -> str:
    """Pesan panduan top up. `banks` = list rekening AKTIF dari DB."""
    if banks:
        bank_lines = []
        for b in banks:
            note = f" — <i>{b.notes}</i>" if b.notes else ""
            bank_lines.append(
                f"   • <b>{b.bank_name}</b>: <code>{b.account_number}</code> a.n. {b.account_holder}{note}"
            )
        bank_block = "\n".join(bank_lines)
    else:
        bank_block = "   <i>Belum ada rekening tersedia. Hubungi admin.</i>"

    return (
        "━━━ 💳 <b>Top Up Saldo</b> ━━━\n\n"
        "📌 Cara top up:\n\n"
        "1️⃣ Transfer ke salah satu rekening berikut:\n"
        f"{bank_block}\n\n"
        "2️⃣ Kirim <b>bukti transfer</b> ke sini sebagai\n"
        "   foto atau dokumen.\n"
        "   Caption wajib: <code>topup &lt;jumlah&gt;</code>\n"
        "   Contoh: <code>topup 50000</code>\n\n"
        "3️⃣ Admin verifikasi → saldo otomatis masuk ✅\n\n"
        "⚠️ Minimal top up: <b>Rp 10.000</b>"
    )


def format_topup_requests(requests: list[object]) -> str:
    if not requests:
        return "✅ Tidak ada permintaan top up yang menunggu persetujuan."
    lines = [f"📋 <b>Top Up Pending ({len(requests)} permintaan)</b>\n"]
    for r in requests:
        uname = f"@{r.username}" if r.username else r.full_name
        lines.append(
            f"🔹 <b>#{r.request_id}</b> — {uname} (<code>{r.user_id}</code>)\n"
            f"   💰 {format_rupiah(r.amount)}\n"
            f"   🕐 {r.created_at[:16]}\n"
            f"   ✅ /approve_{r.request_id}   ❌ /reject_{r.request_id}"
        )
    return "\n\n".join(lines)


def format_admin_logs(logs: list[object]) -> str:
    if not logs:
        return "📭 Belum ada aktivitas admin yang tercatat."
    lines = ["📋 <b>Log Aktivitas Admin (20 terbaru)</b>\n"]
    for log in logs:
        lines.append(
            f"🕐 {log.created_at[:16]}\n"
            f"👤 <b>{log.admin_name}</b>\n"
            f"   ▸ {log.action}"
            + (f": {log.detail}" if log.detail else "")
        )
    return "\n\n".join(lines)


# ── Konfirmasi pembelian ──────────────────────────────────────────────────────

def checkout_confirm_message(product_name: str, price: int, balance: int, category: str) -> str:
    sisa = balance - price
    tipe = "🤖 Otomatis (langsung dikirim)" if category == "otomatis" else "👤 Manual (admin kirim)"
    return (
        f"🛒 <b>Konfirmasi Pembelian</b>\n"
        f"{'━' * 24}\n"
        f"📦 Produk   : <b>{product_name}</b>\n"
        f"💵 Harga    : {format_rupiah(price)}\n"
        f"📂 Tipe     : {tipe}\n"
        f"{'━' * 24}\n"
        f"💰 Saldo    : {format_rupiah(balance)}\n"
        f"💳 Sisa     : <b>{format_rupiah(sisa)}</b>\n"
        f"{'━' * 24}\n\n"
        f"Lanjutkan pembelian?"
    )


# ── Animasi loading payment (multi-step) ─────────────────────────────────────

def payment_loading_steps(product_name: str, price: int) -> list[str]:
    """Kembalikan list teks untuk ditampilkan satu per satu (animasi loading)."""
    return [
        (
            f"⏳ <b>Memproses Pembayaran...</b>\n\n"
            f"🔄 Menghubungi server...\n\n"
            f"📦 Produk : {product_name}\n"
            f"💵 Harga  : {format_rupiah(price)}"
        ),
        (
            f"⏳ <b>Memproses Pembayaran...</b>\n\n"
            f"💳 Memotong saldo...\n\n"
            f"📦 Produk : {product_name}\n"
            f"💵 Harga  : {format_rupiah(price)}"
        ),
        (
            f"⏳ <b>Memproses Pembayaran...</b>\n\n"
            f"📦 Menyiapkan produk...\n\n"
            f"📦 Produk : {product_name}\n"
            f"💵 Harga  : {format_rupiah(price)}"
        ),
    ]


# ── Invoice modern ────────────────────────────────────────────────────────────

def invoice_message(
    product_name: str,
    price: int,
    item_content: str | None,
    remaining_balance: int,
    user_id: int,
    username: str | None,
    is_manual: bool = False,
) -> str:
    now = datetime.now()
    invoice_id = f"INV{now.strftime('%Y%m%d%H%M%S')}{user_id % 1000:03d}"
    uname = f"@{username}" if username else f"UID:{user_id}"
    date_str = now.strftime("%d/%m/%Y %H:%M")

    header = (
        f"╔══════════════════════╗\n"
        f"║  ✅ <b>PEMBAYARAN SUKSES</b>   ║\n"
        f"╚══════════════════════╝\n"
    )

    details = (
        f"\n🧾 <b>INVOICE</b> — <code>{invoice_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Produk    : <b>{product_name}</b>\n"
        f"💵 Harga     : {format_rupiah(price)}\n"
        f"👤 Pembeli   : {uname}\n"
        f"🕐 Waktu     : {date_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 Saldo Sisa: <b>{format_rupiah(remaining_balance)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if is_manual:
        delivery = (
            f"\n📬 <b>Status: Menunggu Pengiriman</b>\n\n"
            f"Produk ini dikirim secara manual oleh admin.\n"
            f"Admin akan segera menghubungimu. ⏳"
        )
    else:
        delivery = (
            f"\n📬 <b>Detail Produk Kamu:</b>\n\n"
            f"<code>{item_content}</code>\n\n"
            f"⚠️ Simpan data ini dengan aman!\n"
            f"Jangan bagikan ke siapapun."
        )

    footer = f"\n\n🙏 Terima kasih telah berbelanja di <b>Ucok Store</b>!"

    return header + details + delivery + footer


# ── Low stock alert ───────────────────────────────────────────────────────────

def low_stock_alert_message(product_name: str, product_id: int, stock: int) -> str:
    emoji = "🔴" if stock == 0 else "🟡"
    label = "STOK HABIS" if stock == 0 else f"STOK MENIPIS ({stock} tersisa)"
    return (
        f"{emoji} <b>ALERT: {label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Produk  : {product_name} (ID: {product_id})\n"
        f"📊 Stok    : {stock} item\n\n"
        f"Upload stok baru:\n"
        f"<code>stok {product_id}</code>"
    )


# ── v7: Edit Produk ───────────────────────────────────────────────────────────

PRODUCT_FIELD_LABELS = {
    "name": "Nama",
    "category": "Kategori",
    "price": "Harga",
    "description": "Deskripsi",
}


def admin_edit_select_id_message() -> str:
    return (
        "✏️ <b>Edit Produk</b>\n\n"
        "Kirim <b>ID produk</b> yang ingin di-edit.\n"
        "Contoh: <code>3</code>\n\n"
        "Lihat daftar ID di menu <b>Lihat Produk</b>."
    )


def admin_edit_product_detail_message(product) -> str:
    """Pesan detail produk yang akan di-edit + petunjuk pilih field."""
    return (
        f"✏️ <b>Edit Produk #{product.product_id}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 Nama      : <b>{product.name}</b>\n"
        f"📂 Kategori  : {product.category}\n"
        f"💵 Harga     : {format_rupiah(product.price)}\n"
        f"📝 Deskripsi : {product.description}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Pilih field yang ingin di-edit di bawah ini 👇"
    )


def admin_edit_field_prompt_message(product, field: str) -> str:
    label = PRODUCT_FIELD_LABELS.get(field, field)
    if field == "name":
        current = product.name
        hint = "Max 100 karakter."
    elif field == "category":
        current = product.category
        hint = "Hanya boleh: <code>otomatis</code> atau <code>manual</code>."
    elif field == "price":
        current = format_rupiah(product.price)
        hint = "Minimal Rp 1.000. Contoh: <code>55000</code>."
    elif field == "description":
        current = product.description
        hint = "Max 500 karakter."
    else:
        current = "-"
        hint = ""
    return (
        f"✏️ <b>Edit {label}</b> — Produk #{product.product_id}\n\n"
        f"Nilai sekarang:\n<code>{current}</code>\n\n"
        f"Kirim nilai baru. {hint}\n"
        f"Ketik <code>/cancel</code> untuk batal."
    )


def admin_edit_success_message(product, field: str, new_value) -> str:
    label = PRODUCT_FIELD_LABELS.get(field, field)
    display_value = format_rupiah(new_value) if field == "price" else str(new_value)
    return (
        f"✅ <b>Field {label} produk #{product.product_id} berhasil diubah.</b>\n\n"
        f"📦 <b>{product.name}</b>\n"
        f"{label} baru: <code>{display_value}</code>"
    )


# ── v7: Maintenance Mode ──────────────────────────────────────────────────────

def maintenance_active_message(custom_msg: str) -> str:
    base = (
        "🛠️ <b>Bot Sedang Pemeliharaan</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if custom_msg:
        base += f"{custom_msg}\n\n"
    base += "Silakan coba lagi nanti. 🙏"
    return base


def maintenance_status_message(active: bool, custom_msg: str) -> str:
    if active:
        return (
            f"✅ <b>Maintenance mode AKTIF</b>\n\n"
            f"Pesan untuk user:\n<i>{custom_msg or '(tidak ada)'}</i>\n\n"
            f"Nonaktifkan: <code>/maintenance off</code>"
        )
    return (
        "✅ <b>Maintenance mode NONAKTIF</b>\n\n"
        "Bot kembali melayani semua user. 🟢"
    )


def maintenance_help_message() -> str:
    return (
        "🛠️ <b>Mode Pemeliharaan</b>\n\n"
        "Aktifkan:\n"
        "<code>/maintenance on Server lagi update, balik 1 jam lagi</code>\n\n"
        "Nonaktifkan:\n"
        "<code>/maintenance off</code>\n\n"
        "Saat aktif, semua user akan diblok kecuali admin.\n"
        "Pesan custom akan ditampilkan ke user."
    )


# ── v7: Kelola Bank ──────────────────────────────────────────────────────────

def format_bank_list_admin(banks: list[object]) -> str:
    """Tampilkan list bank ke admin (termasuk yang nonaktif)."""
    if not banks:
        return (
            "🏦 <b>Daftar Rekening</b>\n\n"
            "Belum ada rekening terdaftar.\n"
            "Tambah lewat menu <b>➕ Tambah Bank</b>."
        )
    lines = ["🏦 <b>Daftar Rekening</b>\n"]
    for b in banks:
        status = "🟢" if b.is_active else "🔴"
        note = f" — <i>{b.notes}</i>" if b.notes else ""
        lines.append(
            f"{status} <b>#{b.bank_id} {b.bank_name}</b>{note}\n"
            f"   <code>{b.account_number}</code> a.n. {b.account_holder}"
        )
    return "\n\n".join(lines)


def admin_bank_menu_message() -> str:
    return (
        "🏦 <b>Kelola Rekening Bank</b>\n\n"
        "Pilih aksi di keyboard:\n"
        "• ➕ Tambah Bank — tambah rekening baru\n"
        "• ✏️ Edit Bank — ubah info rekening\n"
        "• 🔄 Aktif/NonAktifkan — toggle status\n"
        "• 🗑️ Hapus Bank — hapus permanen\n\n"
        "Bank dengan status 🟢 akan muncul di panduan top up user.\n"
        "Bank 🔴 tersembunyi dari user."
    )


def admin_bank_add_message() -> str:
    return (
        "➕ <b>Tambah Rekening Baru</b>\n\n"
        "Kirim dengan format:\n"
        "<code>nama_bank | no_rekening | atas_nama | catatan</code>\n\n"
        "Catatan opsional. Contoh:\n"
        "<code>BNI | 0123456789 | Ucok Store | Bank konvensional</code>\n"
        "<code>DANA | 0812-9999-1234 | Ucok Store</code>"
    )


def admin_bank_edit_id_message() -> str:
    return (
        "✏️ <b>Edit Rekening</b>\n\n"
        "Kirim <b>ID bank</b> yang mau di-edit.\n"
        "Contoh: <code>2</code>"
    )


def admin_bank_edit_field_prompt(bank) -> str:
    return (
        f"✏️ <b>Edit Bank #{bank.bank_id} — {bank.bank_name}</b>\n\n"
        f"Pilih field yang ingin diubah di bawah ini 👇"
    )


BANK_FIELD_LABELS = {
    "bank_name": "Nama Bank",
    "account_number": "Nomor Rekening",
    "account_holder": "Atas Nama",
    "notes": "Catatan",
}


def admin_bank_edit_value_prompt(bank, field: str) -> str:
    label = BANK_FIELD_LABELS.get(field, field)
    current_map = {
        "bank_name": bank.bank_name,
        "account_number": bank.account_number,
        "account_holder": bank.account_holder,
        "notes": bank.notes or "(kosong)",
    }
    current = current_map.get(field, "-")
    return (
        f"✏️ <b>Edit {label} — Bank #{bank.bank_id}</b>\n\n"
        f"Nilai sekarang:\n<code>{current}</code>\n\n"
        f"Kirim nilai baru. /cancel untuk batal."
    )


def admin_bank_toggle_message() -> str:
    return (
        "🔄 <b>Aktif/NonAktifkan Bank</b>\n\n"
        "Kirim <b>ID bank</b> untuk toggle statusnya.\n"
        "Bank aktif (🟢) → nonaktif (🔴), dan sebaliknya."
    )


def admin_bank_delete_message() -> str:
    return (
        "🗑️ <b>Hapus Bank</b>\n\n"
        "Kirim <b>ID bank</b> untuk dihapus permanen.\n"
        "⚠️ Penghapusan tidak bisa dibatalkan."
    )


# ── v7: Daily Login Bonus ─────────────────────────────────────────────────────

def _streak_emoji(streak: int) -> str:
    if streak >= 7:
        return "🔥🔥🔥"
    if streak >= 5:
        return "🔥🔥"
    if streak >= 3:
        return "🔥"
    return "✨"


def daily_bonus_overview_message(info) -> str:
    """Tampilan saat user buka menu Bonus Harian, sebelum klaim."""
    if info.already_claimed:
        return daily_bonus_already_claimed_message(info)
    streak_label = f"Streak ke-{info.streak + 1 if info.streak > 0 else 1}"
    return (
        f"🎁 <b>Bonus Harian</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{_streak_emoji(info.streak + 1)} {streak_label}\n"
        f"💰 Reward       : <b>{format_rupiah(info.next_amount)}</b>\n"
        f"📊 Streak saat ini : {info.streak} hari\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Klik tombol <b>🎁 Klaim Bonus</b> untuk dapat saldo.\n\n"
        f"💡 <i>Tip: Klaim setiap hari berturut-turut untuk reward "
        f"lebih besar! Streak reset jika lewat 1 hari.</i>"
    )


def daily_bonus_success_message(info) -> str:
    return (
        f"🎉 <b>Bonus Harian Diklaim!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{_streak_emoji(info.streak)} Streak: <b>{info.streak} hari</b>\n"
        f"💰 Dapat        : <b>+{format_rupiah(info.claimed_amount)}</b>\n"
        f"💳 Saldo sekarang : <b>{format_rupiah(info.new_balance)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Klaim besok untuk dapat: <b>{format_rupiah(info.next_amount)}</b>\n\n"
        f"Selamat belanja! 🛒"
    )


def daily_bonus_already_claimed_message(info) -> str:
    return (
        f"⏰ <b>Sudah Klaim Hari Ini</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{_streak_emoji(info.streak)} Streak kamu: <b>{info.streak} hari</b>\n"
        f"💰 Klaim besok : <b>{format_rupiah(info.next_amount)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Sampai jumpa besok ya! 👋\n"
        f"⚠️ Streak <b>reset</b> kalau kamu skip 1 hari."
    )
