# Changelog

## [v7.0] - 2026-05-25

### ✨ Fitur Baru

#### ✏️ Edit Produk
- Menu admin baru: `Edit Produk` — kirim ID produk → pilih field via tombol inline.
- Bisa edit `Nama`, `Kategori`, `Harga`, atau `Deskripsi` per-field tanpa harus hapus & buat ulang.
- Input divalidasi & di-sanitasi (escape HTML, cek range harga, validasi kategori).
- Setiap perubahan dicatat di Log Aktivitas Admin.

#### 🛠️ Maintenance Mode
- Command baru: `/maintenance on <pesan>` dan `/maintenance off`.
- `/maintenance` tanpa argumen → tampilkan status + cara pakai.
- Saat aktif: SEMUA user (kecuali admin) di-block dari `start`, callback inline,
  foto, dokumen, dan teks. Mereka menerima pesan custom.
- Admin tetap bisa pakai SEMUA command admin (approve, broadcast, edit, dll).
- Setiap toggle dicatat di Log Aktivitas Admin.
- Pesan custom di-escape HTML untuk keamanan.
- Implementasi via decorator `@maintenance_guard` yang preserve handler names
  pakai `functools.wraps`.

#### 🏦 Multi-Bank Dinamis
- Menu admin baru: `Kelola Bank` dengan sub-keyboard:
  `➕ Tambah Bank` / `✏️ Edit Bank` / `🔄 Aktif/NonAktifkan` / `🗑️ Hapus Bank`
- Rekening sekarang disimpan di DB (tabel `banks`) — bukan hardcoded lagi.
- Field: nama bank, no rekening, atas nama, catatan, status aktif.
- Saat user buka menu Top Up, list rekening DINAMIS dari DB (hanya yang aktif).
- Default seed: BCA + GoPay/OVO disisipkan otomatis saat DB pertama kali dibuat.
- Edit per-field via inline button, sama seperti edit produk.
- Toggle status: aktif (🟢) ⇄ nonaktif (🔴) tanpa hapus data.
- Hapus permanen dengan konfirmasi via ID.
- Setiap aksi (tambah/edit/toggle/hapus) dicatat di Log Aktivitas Admin.

#### 🎁 Daily Login Bonus + Streak
- Tombol baru `🎁 Bonus Harian` di keyboard utama user.
- Command baru: `/bonus`.
- Reward: <b>Rp 500</b> hari pertama, naik +Rp 500 per streak (cap 7 hari = Rp 3.500).
- Klaim 2x dalam 1 hari? Tidak bisa — bot tampilkan "Sudah klaim hari ini".
- Skip 1+ hari? Streak reset ke 1.
- Klaim consecutive? Streak bertambah, reward naik.
- Transaksi bonus pakai type `bonus` (tidak masuk omzet, tidak masuk top buyer count).
- Riwayat transaksi sekarang punya icon 🎁 untuk tipe bonus.
- Tampilan: emoji streak (✨ → 🔥 → 🔥🔥 → 🔥🔥🔥) sesuai panjang streak.

### 🐛 Bug Fix
- **`help_handler` & `ping_handler`** dulu tidak set `parse_mode="HTML"`,
  jadi tag `<b>` bocor sebagai teks. Sekarang fixed.
- **Callback `soldout_noop`** di v6 sebenarnya silent failure karena
  CallbackQueryHandler pattern di app.py hanya match `^(prod_|checkout_)`.
  Tombol "🚫N" di katalog stok-habis di-klik tidak ada respons sama sekali.
  Pattern diperluas jadi `^(prod_|checkout_|soldout_|editprod_|editbank_|bonus_)`.
- **`format_transaction_history`, `format_top_buyers`, `topup_guide_message`,
  `format_admin_logs`, `format_topup_requests`** dipanggil tanpa `parse_mode="HTML"`
  di beberapa handler — tag HTML bocor. Sekarang konsisten pakai HTML mode.

### 🔧 Refactor
- `topup_guide_message()` sekarang menerima parameter `banks` (list dinamis).
- `_handle_admin_menu()` di-extend untuk handle sub-menu Bank (state machine):
  `ADMIN_STATE_BANK_*` family + `_build_admin_bank_keyboard()`.
- 3 tabel baru: `bot_settings` (key-value), `banks`, `daily_bonus_claims`.
- `update_balance()` sekarang juga dipakai untuk tipe `bonus`.
- Tests diperbaharui — 49 unit tests pass (admin_utils + messages smoke tests
  untuk semua fitur baru).

### 🗄️ Schema Migrations
Tabel baru otomatis dibuat saat startup (`initialize_database()` idempotent):
- `bot_settings (key, value, updated_at)` — maintenance flag + pesan custom.
- `banks (id, bank_name, account_number, account_holder, notes, is_active, created_at)`
  + auto-seed 2 rekening default kalau tabel kosong.
- `daily_bonus_claims (user_id, last_claim_date, streak, total_claimed)`.

---

## [v6.0] - 2026-05-25

### 🐛 Bug Fix Kritis

#### Fix #1 — Tombol Batal tidak ada respon
- **Root cause**: `edit_text()` dipanggil untuk pesan yang berisi foto (banner).
  Telegram melempar exception karena foto harus di-edit dengan `edit_caption()`.
  Exception di-`pass` diam-diam → tidak ada response visual ke user.
- **Fix**: Semua blok edit sekarang cek `query.message.photo` terlebih dahulu,
  lalu pilih `edit_caption()` atau `edit_text()` sesuai tipe pesan.
- **Juga**: `query.answer()` dipindah ke SETELAH logika cancel selesai
  agar toast confirmation "Pembelian dibatalkan." muncul di HP user.

#### Fix #2 — Tombol "Beli Sekarang" stok habis tidak ada respon
- **Root cause**: `query.answer()` sudah dipanggil secara global di baris pertama
  handler (baris 253 v5). Telegram hanya membolehkan satu `query.answer()` per
  callback — panggilan kedua dengan `show_alert=True` diabaikan sepenuhnya.
- **Fix**: `query.answer()` global dihapus. Setiap branch sekarang memanggil
  `query.answer()` sendiri — yang butuh `show_alert=True` mendapat alert,
  yang sukses mendapat `answer()` biasa sebelum lanjut proses.

### ✨ Fitur Baru

#### 🚫 Auto Disable Tombol Sold Out
- Tombol nomor produk di katalog otomatis berubah jadi `🚫N` jika stok habis.
- Callback tombol sold out diarahkan ke `soldout_noop` yang tampilkan alert.
- Halaman detail produk habis otomatis tampilkan tombol
  `🚫 Stok Habis — Tidak Tersedia` (tidak bisa diklik untuk beli).
- Label produk di daftar berubah: stok habis ditampilkan dengan strikethrough
  `<s>Nama Produk</s>` dan label `Habis`.

#### 🔄 Auto Refresh Stok Realtime
- Saat user klik tombol Beli, stok di-fetch ulang dari database sebelum proses.
- Jika stok habis sejak terakhir dilihat → alert muncul DAN tombol di-update
  otomatis jadi disabled tanpa user harus refresh manual.
- `beli <id>` via teks juga cek stok realtime sebelum tampilkan konfirmasi.

#### 🎬 Animasi Loading Payment
- Setelah konfirmasi, muncul 3 frame animasi sebelum produk dikirim:
  1. "Menghubungi server..."
  2. "Memotong saldo..."
  3. "Menyiapkan produk..."
- Setiap frame ditampilkan selama 0.8 detik dengan `edit_caption/edit_text`.
- Memberikan feedback visual bahwa transaksi sedang diproses.

#### 🧾 Invoice Modern
- Pesan sukses pembelian diganti menjadi invoice bergaya profesional.
- Format: header `╔══╗`, Invoice ID unik (`INV{tanggal}{user_id}`), detail
  produk, info pembeli, timestamp, saldo sisa, dan konten produk dalam
  `<code>` block.
- Produk manual tampilkan status "Menunggu Pengiriman" yang jelas.
- Footer: "Terima kasih telah berbelanja di Ucok Store!"

#### 💎 UI Premium Telegram Store Style
- `start_message()`: Header box `╔══╗`, section divider `━━━`, format bold
  untuk nama dan saldo.
- `help_message()`: Dibagi per seksi dengan emoji, bold command.
- `format_transaction_history()`: Icon per tipe transaksi (🛒/💰/⚙️), bold label.
- `format_top_buyers()`: Layout dua baris per entry, dot separator.
- `format_product_list()` (admin): Icon 🟢/🔴 per status stok.
- `topup_guide_message()`: Rekening dalam `<code>` block, step bernomor.
- `format_topup_requests()`: Bullet 🔹 per request.
- `admin_welcome_message()`, `admin_product_input_message()`, dll: HTML format.
- `checkout_confirm_message()`: Divider `━━━` di antara section.

---

## [v5.0] - 2026-05-25
- Checkout flow (konfirmasi pembelian)
- Notifikasi stok hampir habis
- Log aktivitas admin
- Keamanan: cegah saldo negatif atomic, sanitasi input produk

## [v2.0] - 2026-05-24
- Fitur Broadcast (teks, foto, dokumen)
- Panel admin lengkap

## [v1.0] - Initial Release
- Fitur dasar: list produk, pembelian, top up saldo
