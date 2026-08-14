# Netflix Cookie Cleanup Script

Script standalone untuk memvalidasi dan mengorganisasi cookies Netflix.

## Fitur

- ✅ Scan cookies di `stok/netflix/`
- ✅ Validasi via Netflix API
- ✅ Organisir valid cookies ke `{Country}/{Plan}/`
- ✅ Hapus dead cookies otomatis
- ✅ Support proxy rotation
- ✅ Real-time progress tracking

## Cara Pakai

### Langsung dari Terminal

```bash
cd scripts/cleanup
python cleanup_cookies.py
```

### Dari Bot Telegram

Bot akan otomatis memanggil script ini melalui Web Checker API saat admin menjalankan `/cleanup run`.

## Konfigurasi

### Proxy (Opsional)

Edit file `proxy.txt` untuk menambahkan proxy:

```
# Format:
host:port
user:pass:host:port
http://user:pass@host:port
```

Contoh:
```
192.168.1.1:8080
myuser:mypass:proxy.example.com:3128
```

## Output

Script akan:
1. Scan semua file `.txt` dan `.json` di `stok/netflix/`
2. Validate setiap cookie via Netflix API
3. Cookie valid → pindah ke `stok/netflix/{Country}/{Plan}/`
4. Cookie mati → hapus file
5. Print statistik hasil cleanup

## Integrasi dengan Bot

Script ini dipanggil oleh:
- **Bot Handler:** `telegram_bot/cleanup_handler.py`
- **Web Checker:** `scripts/webchecker/app.py` endpoint `/api/cleanup`

## Troubleshooting

**Error: "Directory tidak ditemukan"**
- Pastikan folder `stok/netflix/` ada di root project

**Error: "No cookie files found"**
- Pastikan ada file `.txt` atau `.json` di `stok/netflix/`
- Script hanya scan di root level (tidak termasuk subdirectories)

**Banyak cookies mati**
- Coba gunakan proxy dengan edit `proxy.txt`
- Beberapa cookies mungkin memang expired

## Technical Details

- **Timeout:** 20 detik per request
- **Supported Formats:** Netscape `.txt` dan JSON
- **Validation Endpoint:** `https://www.netflix.com/account/membership`
- **SSL Verification:** Disabled (untuk kompatibilitas proxy)
