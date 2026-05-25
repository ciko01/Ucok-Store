# Ucok Store — Telegram Bot

Bot toko digital berbasis Python dengan fitur lengkap: beli produk otomatis/manual, top up saldo, riwayat transaksi, leaderboard pembeli, broadcast, **edit produk**, **multi-bank dinamis**, **daily login bonus**, dan **maintenance mode**.

## Fitur

### User
- `/start` — halaman utama dengan profil & statistik bot
- `/help` — daftar command
- `/ping` — cek bot online
- `/myid` — lihat Telegram ID kamu
- `/bonus` — klaim bonus harian (streak counter)
- `/cancel` — batalkan operasi aktif
- **List Produk** — lihat produk otomatis & manual; beli dengan ketik `beli <id>`
- **Riwayat Transaksi** — 10 transaksi terakhir (icon per tipe)
- **Top Five Buyer** — leaderboard pembeli terbanyak
- **Top Up Saldo** — kirim bukti transfer (foto/file) dengan caption `topup <jumlah>`
- **🎁 Bonus Harian** — klaim saldo gratis setiap hari (streak Rp 500–3.500)

### Pembelian
- **Produk Otomatis**: stok langsung dikirim ke chat setelah bayar
- **Produk Manual**: admin diberitahu dan mengirim secara manual
- Konfirmasi checkout sebelum bayar (10 menit expiry)
- Animasi loading + invoice modern dengan Invoice ID unik
- Auto-disable tombol Beli saat stok habis (realtime cek)

### Admin (`/admin`)
- Tambah produk (`nama | kategori | harga | deskripsi`)
- **Edit produk** — ubah nama/kategori/harga/deskripsi per field via inline button
- Upload stok `.txt` per produk
- Lihat semua produk & stok
- Hapus/nonaktifkan produk
- **Kelola Bank** — tambah/edit/toggle/hapus rekening dinamis untuk top up
- Lihat permintaan top up pending
- `/approve_<id>` — setujui top up (saldo langsung masuk)
- `/reject_<id>` — tolak top up
- `/bc` — **BROADCAST** pesan ke semua user (teks, foto, atau dokumen)
- `/stats` — statistik lengkap bot
- `/addbal <uid> <jumlah>` — ubah saldo user (positif/negatif)
- `/maintenance on <pesan>` / `/maintenance off` — mode pemeliharaan

## Cara pakai

1. Salin `.env.example` menjadi `.env`
2. Isi `BOT_TOKEN` dari [@BotFather](https://t.me/BotFather)
3. Isi `ADMIN_IDS` dengan user ID Telegram admin (pisah koma jika lebih dari satu)
4. Opsional: isi `BOT_NAME`, taruh banner di `assets/start-banner.jpg`
5. Install dependency:

```bash
pip install -r requirements.txt
```

6. Jalankan:

```bash
python main.py
```

## Fitur Daily Login Bonus (v7)

- Tombol **🎁 Bonus Harian** di keyboard utama atau command `/bonus`.
- Reward berbasis **streak**:
  | Streak | Reward |
  |---|---|
  | Hari 1 | Rp 500 |
  | Hari 2 | Rp 1.000 |
  | Hari 3 | Rp 1.500 |
  | Hari 4 | Rp 2.000 |
  | Hari 5 | Rp 2.500 |
  | Hari 6 | Rp 3.000 |
  | Hari 7+ | Rp 3.500 (max) |
- Skip 1 hari → streak reset ke 1.
- Klaim 2x sehari? Tidak bisa, bot tolak otomatis dengan pesan jelas.
- Tipe transaksi `bonus` — tidak dihitung sebagai omzet atau pembelian.

## Fitur Edit Produk (v7)

1. Admin → `Edit Produk`
2. Kirim ID produk → bot tampilkan detail + inline button per field
3. Klik tombol field (`✏️ Nama`, `📂 Kategori`, `💵 Harga`, `📝 Deskripsi`)
4. Kirim nilai baru → bot validasi + sanitasi → update + audit log

## Fitur Multi-Bank Dinamis (v7)

- Admin → `Kelola Bank` → sub-menu (`➕ Tambah` / `✏️ Edit` / `🔄 Toggle` / `🗑️ Hapus`)
- Format tambah: `nama_bank | no_rekening | atas_nama | catatan(opsional)`
- Toggle status: bank tetap di DB tapi tidak muncul ke user (🔴)
- Edit per field via inline button
- User di menu Top Up melihat list bank dinamis dari DB (hanya 🟢)
- Default seed: BCA + GoPay/OVO saat database pertama kali dibuat

## Fitur Maintenance Mode (v7)

- `/maintenance on Server lagi update, balik 1 jam lagi` → block semua user non-admin
- `/maintenance off` → buka kembali
- `/maintenance` → cek status sekarang + petunjuk
- Saat aktif: user non-admin menerima pesan custom HTML-escaped, semua handler terblok
- Admin tetap bisa pakai semua menu & command — termasuk approve top up, broadcast, dll
- Implementasi via decorator `@maintenance_guard` di handler entry-point

## Alur Top Up

1. User ketik menu **Top Up Saldo** → lihat info rekening (dinamis dari DB)
2. User transfer → kirim foto/file bukti dengan caption `topup 50000`
3. Admin menerima notifikasi + bukti transfer di chat
4. Admin ketik `/approve_<id>` untuk setujui atau `/reject_<id>` untuk tolak
5. Saldo otomatis masuk ke wallet user + notifikasi dikirim ke user

## Fitur Broadcast

Admin dapat mengirim pesan ke semua user yang pernah menggunakan bot:

1. Ketik `/bc` untuk aktifkan mode broadcast
2. Kirim pesan yang ingin di-broadcast:
   - **Teks** (support HTML formatting: `<b>bold</b>`, `<i>italic</i>`, `<code>code</code>`)
   - **Foto** dengan caption (opsional)
   - **Dokumen** dengan caption (opsional)
3. Bot akan mengirim ke semua user dan memberikan laporan hasil (berhasil/gagal)
4. Ketik `/cancel` untuk membatalkan broadcast

## Struktur

```
main.py                  — entry point
telegram_bot/
  config.py              — load .env & validasi
  app.py                 — register semua handler
  handlers.py            — logika routing & semua fitur (~2000 baris)
  messages.py            — semua teks pesan & format HTML
  stats.py               — operasi database SQLite (11 tabel)
  admin_utils.py         — parser & sanitasi input (produk, bank, maintenance, top up)
  product_browser.py     — katalog paginate + inline keyboard
assets/
  start-banner.jpg       — banner /start (opsional)
bot_data.sqlite3         — database otomatis saat bot dijalankan
tests/
  test_admin_utils.py    — 20 tests untuk parser
  test_messages.py       — 29 smoke tests untuk semua formatter
```

## Database

| Tabel | Isi |
|---|---|
| `users` | Profil user |
| `wallets` | Saldo per user |
| `transactions` | Semua riwayat (purchase/topup/adjustment/bonus) |
| `products` | Daftar produk |
| `product_stock` | Stok item per produk |
| `topup_requests` | Permintaan top up + status |
| `admin_logs` | Log aksi admin (v5+) |
| `pending_checkouts` | Checkout menunggu konfirmasi (v5+) |
| `bot_settings` | Key-value (v7: maintenance flag + pesan custom) |
| `banks` | Rekening dinamis untuk top up (v7) |
| `daily_bonus_claims` | Tracking streak bonus harian (v7) |

## Testing

```bash
python -m unittest discover tests -v
```

Total: 49 tests (parser + smoke tests untuk semua formatter & fitur v7).
