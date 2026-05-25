"""Smoke tests untuk messages.py — verifikasi return tipe & key strings.

NOTE: Tests v1 lama sengaja dibuang karena format pesan sudah berubah total
sejak v6 (HTML + emoji + box headers). Lihat CHANGELOG untuk detailnya.
"""
import unittest
from datetime import datetime

from telegram_bot.messages import (
    MENU_BACK,
    MENU_PRODUCTS,
    StartProfile,
    admin_bank_add_message,
    admin_bank_menu_message,
    admin_edit_product_detail_message,
    balance_menu_label,
    daily_bonus_already_claimed_message,
    daily_bonus_overview_message,
    daily_bonus_success_message,
    echo_message,
    format_bank_list_admin,
    format_indonesian_datetime,
    format_rupiah,
    help_message,
    maintenance_active_message,
    maintenance_status_message,
    menu_message,
    ping_message,
    start_message,
    topup_guide_message,
)


class _FakeProduct:
    def __init__(self, pid=1, name="Netflix", category="otomatis", price=50000, description="Akun"):
        self.product_id = pid
        self.name = name
        self.category = category
        self.price = price
        self.description = description


class _FakeBank:
    def __init__(self, bid=1, name="BCA", num="123", holder="Ucok", notes="", active=True):
        self.bank_id = bid
        self.bank_name = name
        self.account_number = num
        self.account_holder = holder
        self.notes = notes
        self.is_active = active


class _FakeBonus:
    def __init__(self, claimed=500, streak=1, next_amount=1000, balance=500, already=False):
        self.claimed_amount = claimed
        self.streak = streak
        self.next_amount = next_amount
        self.new_balance = balance
        self.already_claimed = already
        self.success = not already


class CoreMessageTests(unittest.TestCase):
    def test_format_rupiah(self):
        self.assertEqual("Rp 9.956.157", format_rupiah(9956157))
        self.assertEqual("Rp 500", format_rupiah(500))

    def test_balance_menu_label(self):
        self.assertEqual("Saldo: Rp 9.956.157", balance_menu_label(9956157))

    def test_format_indonesian_datetime(self):
        self.assertEqual(
            "Minggu, 04 Januari 2026 08:04",
            format_indonesian_datetime(datetime(2026, 1, 4, 8, 4)),
        )

    def test_start_message_contains_html_and_profile(self):
        msg = start_message(StartProfile(
            full_name="Ucok",
            username="ucok",
            user_id=42,
            balance=10000,
            total_users=5,
            total_transactions=10,
            current_time=datetime(2026, 5, 25, 9, 0),
        ))
        self.assertIn("<b>UCOK STORE</b>", msg)
        self.assertIn("Ucok", msg)
        self.assertIn("@ucok", msg)
        self.assertIn("Rp 10.000", msg)

    def test_help_message_lists_commands(self):
        msg = help_message()
        for cmd in ["/start", "/help", "/ping", "/bonus", "/maintenance"]:
            self.assertIn(cmd, msg)

    def test_ping_uses_html(self):
        self.assertIn("<b>", ping_message())

    def test_echo_message(self):
        self.assertIn("halo", echo_message("halo"))
        self.assertIn("pesan kosong", echo_message("   "))

    def test_menu_message_for_products_html(self):
        self.assertIn("<b>", menu_message(MENU_PRODUCTS))

    def test_menu_message_for_back(self):
        self.assertIn("menu utama", menu_message(MENU_BACK))


class TopupGuideTests(unittest.TestCase):
    def test_empty_banks(self):
        msg = topup_guide_message([])
        self.assertIn("Belum ada rekening", msg)

    def test_with_banks(self):
        banks = [_FakeBank(name="BCA", num="123", holder="Ucok")]
        msg = topup_guide_message(banks)
        self.assertIn("BCA", msg)
        self.assertIn("123", msg)
        self.assertIn("Ucok", msg)

    def test_with_notes(self):
        banks = [_FakeBank(notes="E-Wallet")]
        msg = topup_guide_message(banks)
        self.assertIn("E-Wallet", msg)


class EditProductMessageTests(unittest.TestCase):
    def test_detail_contains_fields(self):
        msg = admin_edit_product_detail_message(_FakeProduct())
        self.assertIn("Netflix", msg)
        self.assertIn("Rp 50.000", msg)
        self.assertIn("otomatis", msg)


class BankMessageTests(unittest.TestCase):
    def test_format_empty(self):
        self.assertIn("Belum ada rekening", format_bank_list_admin([]))

    def test_format_with_banks(self):
        banks = [_FakeBank(name="BCA", active=True), _FakeBank(bid=2, name="BNI", active=False)]
        msg = format_bank_list_admin(banks)
        self.assertIn("🟢", msg)  # active
        self.assertIn("🔴", msg)  # inactive
        self.assertIn("BCA", msg)
        self.assertIn("BNI", msg)

    def test_menu_message(self):
        self.assertIn("Tambah Bank", admin_bank_menu_message())

    def test_add_message(self):
        self.assertIn("nama_bank", admin_bank_add_message())


class MaintenanceMessageTests(unittest.TestCase):
    def test_active_message_with_custom(self):
        msg = maintenance_active_message("Update server")
        self.assertIn("Update server", msg)
        self.assertIn("Pemeliharaan", msg)

    def test_active_message_without_custom(self):
        msg = maintenance_active_message("")
        self.assertIn("Pemeliharaan", msg)

    def test_status_on(self):
        msg = maintenance_status_message(True, "Lagi update")
        self.assertIn("AKTIF", msg)
        self.assertIn("Lagi update", msg)

    def test_status_off(self):
        msg = maintenance_status_message(False, "")
        self.assertIn("NONAKTIF", msg)


class DailyBonusMessageTests(unittest.TestCase):
    def test_overview_not_claimed(self):
        info = _FakeBonus(streak=0, next_amount=500, already=False)
        msg = daily_bonus_overview_message(info)
        self.assertIn("Klaim", msg)
        self.assertIn("Rp 500", msg)

    def test_overview_already_claimed_delegates(self):
        info = _FakeBonus(streak=3, next_amount=2000, already=True)
        msg = daily_bonus_overview_message(info)
        # already_claimed → delegates to daily_bonus_already_claimed_message
        self.assertIn("Sudah Klaim", msg)

    def test_success_message(self):
        info = _FakeBonus(claimed=1500, streak=3, next_amount=2000, balance=4500)
        msg = daily_bonus_success_message(info)
        self.assertIn("+Rp 1.500", msg)
        self.assertIn("3 hari", msg)
        self.assertIn("Rp 4.500", msg)

    def test_already_claimed_message(self):
        info = _FakeBonus(streak=5, next_amount=3000, already=True)
        msg = daily_bonus_already_claimed_message(info)
        self.assertIn("5 hari", msg)
        self.assertIn("Rp 3.000", msg)


if __name__ == "__main__":
    unittest.main()
