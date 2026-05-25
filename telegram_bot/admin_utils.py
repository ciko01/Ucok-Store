from __future__ import annotations

import html
import re
from dataclasses import dataclass

MAX_NAME_LENGTH = 100
MAX_DESC_LENGTH = 500
MIN_PRICE = 1_000
MIN_TOPUP = 10_000
MAX_BANK_NAME_LENGTH = 50
MAX_ACCOUNT_LENGTH = 50
MAX_HOLDER_LENGTH = 100
MAX_NOTES_LENGTH = 100
MAX_MAINTENANCE_MSG_LENGTH = 500


@dataclass(frozen=True)
class ProductDraft:
    name: str
    category: str
    price: int
    description: str


@dataclass(frozen=True)
class BankDraft:
    bank_name: str
    account_number: str
    account_holder: str
    notes: str


def _sanitize_text(text: str, max_length: int, field_name: str) -> str:
    """Strip, batasi panjang, dan escape HTML dari input teks."""
    clean = text.strip()
    if not clean:
        raise ValueError(f"{field_name} tidak boleh kosong.")
    if len(clean) > max_length:
        raise ValueError(f"{field_name} terlalu panjang (max {max_length} karakter).")
    # Escape karakter HTML agar tidak bisa inject tag ke pesan bot
    return html.escape(clean)


def parse_product_input(text: str) -> ProductDraft:
    parts = [item.strip() for item in text.split("|")]
    if len(parts) != 4:
        raise ValueError(
            "Format harus: nama | kategori | harga | deskripsi\n\n"
            "Contoh:\n"
            "Netflix 1P1U | otomatis | 50000 | Akun private 1 profile 1 user"
        )

    name_raw, category_raw, price_raw, description_raw = parts

    name = _sanitize_text(name_raw, MAX_NAME_LENGTH, "Nama produk")
    description = _sanitize_text(description_raw, MAX_DESC_LENGTH, "Deskripsi")

    category = category_raw.strip().lower()
    if category not in {"otomatis", "manual"}:
        raise ValueError("Kategori harus `otomatis` atau `manual`.")

    # Bersihkan titik/koma dari harga (misal: 50.000 atau 50,000)
    price_clean = re.sub(r"[.,]", "", price_raw.strip())
    if not price_clean.isdigit():
        raise ValueError("Harga harus berupa angka. Contoh: 50000")
    price = int(price_clean)
    if price < MIN_PRICE:
        raise ValueError(f"Harga minimal Rp {MIN_PRICE:,}".replace(",", "."))

    return ProductDraft(
        name=name,
        category=category,
        price=price,
        description=description,
    )


def parse_stock_caption(caption: str | None) -> int:
    if not caption:
        raise ValueError("Caption file wajib diisi dengan format: stok <id_produk>")
    parts = caption.strip().split()
    if len(parts) != 2 or parts[0].lower() != "stok" or not parts[1].isdigit():
        raise ValueError("Format caption harus: stok <id_produk>\nContoh: stok 3")
    return int(parts[1])


def parse_topup_caption(caption: str | None) -> int:
    """Parse caption bukti top up. Format: topup <jumlah>"""
    if not caption:
        raise ValueError(
            "Caption wajib diisi dengan format: topup <jumlah>\nContoh: topup 50000"
        )
    parts = caption.strip().split()
    if len(parts) != 2 or parts[0].lower() != "topup":
        raise ValueError(
            "Format caption salah. Gunakan: topup <jumlah>\nContoh: topup 50000"
        )
    amount_raw = re.sub(r"[.,]", "", parts[1])
    if not amount_raw.isdigit():
        raise ValueError("Jumlah top up harus berupa angka.\nContoh: topup 50000")
    amount = int(amount_raw)
    if amount < MIN_TOPUP:
        raise ValueError(f"Minimal top up adalah {MIN_TOPUP:,}".replace(",", ".") + ".")
    if amount > 100_000_000:
        raise ValueError("Jumlah top up terlalu besar. Hubungi admin secara langsung.")
    return amount


# ── v7: parsers tambahan ──────────────────────────────────────────────────────

def parse_price_value(text: str) -> int:
    """Parse string harga (50000, 50.000, 50,000) → int. Validasi minimum."""
    cleaned = re.sub(r"[.,\s]", "", (text or "").strip())
    if not cleaned.isdigit():
        raise ValueError("Harga harus berupa angka. Contoh: 50000")
    price = int(cleaned)
    if price < MIN_PRICE:
        raise ValueError(f"Harga minimal Rp {MIN_PRICE:,}".replace(",", "."))
    return price


def parse_category_value(text: str) -> str:
    """Validasi kategori produk."""
    category = (text or "").strip().lower()
    if category not in {"otomatis", "manual"}:
        raise ValueError("Kategori harus `otomatis` atau `manual`.")
    return category


def parse_product_field_value(field: str, raw_value: str) -> object:
    """Validasi + sanitasi nilai baru untuk satu field produk."""
    if field == "name":
        return _sanitize_text(raw_value, MAX_NAME_LENGTH, "Nama produk")
    if field == "description":
        return _sanitize_text(raw_value, MAX_DESC_LENGTH, "Deskripsi")
    if field == "price":
        return parse_price_value(raw_value)
    if field == "category":
        return parse_category_value(raw_value)
    raise ValueError(f"Field '{field}' tidak dikenal.")


def parse_bank_input(text: str) -> BankDraft:
    """Parse input tambah bank.

    Format: nama_bank | no_rekening | atas_nama | catatan(opsional)
    """
    parts = [item.strip() for item in (text or "").split("|")]
    if len(parts) not in (3, 4):
        raise ValueError(
            "Format harus: nama_bank | no_rekening | atas_nama | catatan(opsional)\n\n"
            "Contoh:\n"
            "BNI | 0123456789 | Ucok Store | Bank konvensional"
        )
    bank_name = _sanitize_text(parts[0], MAX_BANK_NAME_LENGTH, "Nama bank")
    account_number = _sanitize_text(parts[1], MAX_ACCOUNT_LENGTH, "Nomor rekening")
    account_holder = _sanitize_text(parts[2], MAX_HOLDER_LENGTH, "Atas nama")
    notes = ""
    if len(parts) == 4 and parts[3]:
        notes = _sanitize_text(parts[3], MAX_NOTES_LENGTH, "Catatan")
    return BankDraft(
        bank_name=bank_name,
        account_number=account_number,
        account_holder=account_holder,
        notes=notes,
    )


def parse_bank_field_value(field: str, raw_value: str) -> str:
    """Validasi + sanitasi nilai untuk edit satu field bank."""
    limits = {
        "bank_name": (MAX_BANK_NAME_LENGTH, "Nama bank"),
        "account_number": (MAX_ACCOUNT_LENGTH, "Nomor rekening"),
        "account_holder": (MAX_HOLDER_LENGTH, "Atas nama"),
        "notes": (MAX_NOTES_LENGTH, "Catatan"),
    }
    if field not in limits:
        raise ValueError(f"Field '{field}' tidak dikenal.")
    max_len, label = limits[field]
    if field == "notes" and not (raw_value or "").strip():
        return ""
    return _sanitize_text(raw_value, max_len, label)


def parse_maintenance_command(args: list[str]) -> tuple[bool, str]:
    """Parse /maintenance on|off <pesan>.

    Return (active, message). Raise ValueError jika format salah.
    """
    if not args:
        raise ValueError(
            "Format: /maintenance on <pesan> ATAU /maintenance off\n"
            "Contoh: /maintenance on Server lagi update, balik 1 jam lagi"
        )
    mode = args[0].strip().lower()
    if mode not in {"on", "off"}:
        raise ValueError("Mode harus `on` atau `off`.")
    if mode == "off":
        return False, ""
    message = " ".join(args[1:]).strip()
    if len(message) > MAX_MAINTENANCE_MSG_LENGTH:
        raise ValueError(
            f"Pesan maintenance terlalu panjang (max {MAX_MAINTENANCE_MSG_LENGTH} karakter)."
        )
    # Escape HTML untuk keamanan pesan
    safe_message = html.escape(message) if message else ""
    return True, safe_message
