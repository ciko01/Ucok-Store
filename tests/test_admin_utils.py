import unittest

from telegram_bot.admin_utils import (
    parse_bank_field_value,
    parse_bank_input,
    parse_maintenance_command,
    parse_product_field_value,
    parse_product_input,
    parse_stock_caption,
    parse_topup_caption,
)


class ProductInputTests(unittest.TestCase):
    def test_parse_product_input(self):
        draft = parse_product_input(
            "Netflix 1P1U | otomatis | 50000 | Akun private 1 profile 1 user"
        )
        self.assertEqual("Netflix 1P1U", draft.name)
        self.assertEqual("otomatis", draft.category)
        self.assertEqual(50000, draft.price)

    def test_parse_product_input_rejects_invalid_category(self):
        with self.assertRaises(ValueError):
            parse_product_input("Netflix | digital | 50000 | Desc")

    def test_parse_product_input_rejects_low_price(self):
        with self.assertRaises(ValueError):
            parse_product_input("Netflix | otomatis | 500 | Desc")

    def test_parse_stock_caption(self):
        self.assertEqual(12, parse_stock_caption("stok 12"))

    def test_parse_stock_caption_rejects_invalid_format(self):
        with self.assertRaises(ValueError):
            parse_stock_caption("stokproduk 12")

    def test_parse_topup_caption_ok(self):
        self.assertEqual(50000, parse_topup_caption("topup 50000"))
        self.assertEqual(50000, parse_topup_caption("topup 50.000"))

    def test_parse_topup_caption_rejects_below_min(self):
        with self.assertRaises(ValueError):
            parse_topup_caption("topup 5000")


class EditProductFieldTests(unittest.TestCase):
    def test_edit_name_sanitized(self):
        result = parse_product_field_value("name", "  Netflix Premium  ")
        self.assertEqual("Netflix Premium", result)

    def test_edit_name_escapes_html(self):
        result = parse_product_field_value("name", "<script>evil</script>")
        self.assertIn("&lt;script&gt;", result)
        self.assertNotIn("<script>", result)

    def test_edit_price_valid(self):
        self.assertEqual(75000, parse_product_field_value("price", "75000"))
        self.assertEqual(75000, parse_product_field_value("price", "75.000"))
        self.assertEqual(75000, parse_product_field_value("price", "75,000"))

    def test_edit_price_rejects_below_min(self):
        with self.assertRaises(ValueError):
            parse_product_field_value("price", "500")

    def test_edit_category_valid(self):
        self.assertEqual("otomatis", parse_product_field_value("category", "OTOMATIS"))
        self.assertEqual("manual", parse_product_field_value("category", " manual "))

    def test_edit_category_rejects_invalid(self):
        with self.assertRaises(ValueError):
            parse_product_field_value("category", "digital")

    def test_unknown_field(self):
        with self.assertRaises(ValueError):
            parse_product_field_value("unknown", "value")


class BankInputTests(unittest.TestCase):
    def test_parse_bank_input_three_fields(self):
        draft = parse_bank_input("BNI | 0123456789 | Ucok Store")
        self.assertEqual("BNI", draft.bank_name)
        self.assertEqual("0123456789", draft.account_number)
        self.assertEqual("Ucok Store", draft.account_holder)
        self.assertEqual("", draft.notes)

    def test_parse_bank_input_four_fields(self):
        draft = parse_bank_input("DANA | 0812 | Ucok | E-Wallet")
        self.assertEqual("DANA", draft.bank_name)
        self.assertEqual("E-Wallet", draft.notes)

    def test_parse_bank_input_rejects_too_few(self):
        with self.assertRaises(ValueError):
            parse_bank_input("BNI | 0123")

    def test_bank_field_value_notes_can_be_empty(self):
        self.assertEqual("", parse_bank_field_value("notes", "  "))

    def test_bank_field_value_unknown_field(self):
        with self.assertRaises(ValueError):
            parse_bank_field_value("ip_address", "1.2.3.4")


class MaintenanceCommandTests(unittest.TestCase):
    def test_off(self):
        active, msg = parse_maintenance_command(["off"])
        self.assertFalse(active)
        self.assertEqual("", msg)

    def test_on_with_message(self):
        active, msg = parse_maintenance_command(["on", "Server", "update"])
        self.assertTrue(active)
        self.assertEqual("Server update", msg)

    def test_on_escapes_html(self):
        active, msg = parse_maintenance_command(["on", "<b>important</b>"])
        self.assertTrue(active)
        self.assertIn("&lt;b&gt;", msg)

    def test_no_args_raises(self):
        with self.assertRaises(ValueError):
            parse_maintenance_command([])

    def test_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            parse_maintenance_command(["pause"])


if __name__ == "__main__":
    unittest.main()
