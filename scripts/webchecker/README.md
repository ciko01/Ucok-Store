# Netflix Cookie Checker - Web Service

Fast multi-threaded Netflix cookie validator with FastAPI backend and WebSocket real-time updates.  
Integrated into Ucok Store admin panel.

---

## 🚀 Quick Start

### Run as Part of Ucok Store (Recommended)
```bash
# From project root
python run_complete.py
```
Service akan jalan di: **http://localhost:8001**

### Run Standalone
```bash
# From webchecker directory
cd webchecker
python app.py
```

---

## 📦 Requirements

```bash
pip install -r requirements.txt
```

Optional for SOCKS proxies:
```bash
pip install requests[socks]
```

---

## ✨ Features

### Core Features
- ✅ Multi-threaded cookie checking (24 workers)
- ✅ Real-time progress tracking via WebSocket
- ✅ Automatic plan classification (Premium, Standard, Basic, Free)
- ✅ Extra member detection
- ✅ On-hold account detection
- ✅ Duplicate filtering
- ✅ Stop checking anytime
- ✅ Proxy rotation support
- ✅ NFToken generation (optional)

### Web Interface (Integrated with Ucok Store)
- ✅ Drag & drop file upload (txt, json, zip)
- ✅ Live progress bar updates
- ✅ Real-time statistics
- ✅ Download results per category
- ✅ Collapsible category view
- ✅ Dark theme Netflix-style UI

---

## 📋 Supported Cookie Formats

### Netscape Format (.txt)
```
.netflix.com	TRUE	/	TRUE	1735689600	NetflixId	xxx
.netflix.com	TRUE	/	TRUE	1735689600	SecureNetflixId	xxx
.netflix.com	TRUE	/	TRUE	1735689600	nfvdid	xxx
```

### JSON Format (.json)
```json
[
  {
    "domain": ".netflix.com",
    "name": "NetflixId",
    "value": "xxx",
    "path": "/",
    "secure": true,
    "expires": 1735689600
  }
]
```

### ZIP Archive
- Upload multiple cookie files as .zip
- Auto-extract and validate all files inside

---

## 🔧 Configuration

Edit `config.yml` to customize:

```yaml
# NFToken generation
nftoken: false  # false | "pc" | "mobile" | "both"

# Output fields in txt files
txt_fields:
  name: false
  email: false
  plan: true
  country: true
  max_streams: true
  plan_price: true
  next_billing: true
  payment_method: true
  profiles: true

# Performance tuning
performance:
  request_timeout_seconds: 15
  fallback_account_page: false
  retry_incomplete_info: false
  nftoken_for_free: false

# Retry settings
retries:
  error_proxy_attempts: 3
  nftoken_attempts: 1
```

---

## 🌐 API Endpoints

### POST `/api/check`
Upload dan start checking cookies
- **Request:** `multipart/form-data` with file
- **Response:** `{session_id, total_cookies, message}`

### WebSocket `/ws/{client_id}`
Real-time updates for checking session
- **Events:** `progress`, `valid_account`, `complete`, `stopped`, `error`

### GET `/api/session/{session_id}/progress`
Get current session progress
- **Response:** `{session_id, total, checked, percentage, is_running}`

### GET `/api/session/{session_id}/results`
Get all checking results
- **Response:** `{session_id, summary, accounts}`

### GET `/api/session/{session_id}/download/{category}`
Download results per category as text file
- **Categories:** `premium`, `standard`, `basic`, `free`, `on_hold`, etc

### POST `/api/session/{session_id}/stop`
Stop checking session immediately
- **Response:** `{message: "Checking stopped"}`

---

## 🔌 Proxy Support

Create/edit `proxy.txt` in webchecker directory:

```
# Supported formats (one per line):
ip:port
user:pass@ip:port
http://user:pass@ip:port
socks5://user:pass@ip:port
```

Proxy rotates automatically between retries.

---

## 📁 File Structure

```
webchecker/
├── app.py                 # FastAPI service (port 8001)
├── config.yml             # Configuration
├── proxy.txt              # Proxy list (optional)
├── requirements.txt       # Dependencies
├── LICENSE                # MIT License
├── cookies/               # Input folder (CLI mode)
├── output/                # Results folder
├── failed/                # Failed cookies
├── broken/                # Broken/retry-exhausted cookies
└── static/                # Static assets (if any)
```

---

## 🛠️ Standalone CLI Tool

For CLI-only usage without web interface:

```bash
cd scripts/webchecker
python main.py
```

See: `scripts/webchecker/main.py` (moved from this directory)

---

## 📊 Output Classification

Accounts are classified into:

| Category | Description |
|----------|-------------|
| **Premium** | Full premium accounts |
| **Premium (Extra Member)** | Extra member accounts |
| **Standard** | Standard plan accounts |
| **Standard With Ads** | Standard with ads plan |
| **Basic** | Basic plan accounts |
| **Mobile** | Mobile-only plan |
| **Free** | Free accounts (no subscription) |
| **On Hold** | Subscribed but on-hold status |
| **Unknown** | Cannot determine plan |

---

## 🔍 How It Works

1. **Upload** - User uploads cookie file(s)
2. **Parse** - Extract NetflixId, SecureNetflixId, nfvdid
3. **Validate** - Check cookies against Netflix API
4. **Extract** - Parse account info (plan, email, country, etc)
5. **Classify** - Sort into categories
6. **Broadcast** - Send real-time updates via WebSocket
7. **Save** - Store results and allow download

---

## ⚙️ Integration with Ucok Store

This service is integrated into the main Ucok Store application:

- **Access:** Admin Panel → Web Checker menu
- **URL:** http://localhost:3000/web-checker
- **API Port:** 8001 (this service)
- **Webapp Port:** 3000 (Next.js admin panel)

---

## 🐛 Troubleshooting

### WebSocket disconnected
- Refresh browser page
- Check server is running
- Check firewall/antivirus blocking WebSocket

### Upload fails "No valid cookies"
- Verify cookie format (Netscape or JSON)
- Ensure NetflixId cookie exists
- Try with `sample_cookies.txt` (in `scripts/webchecker/`)

### Checking very slow
- Add proxies to `proxy.txt`
- Reduce `request_timeout_seconds` in config
- Check network connectivity

### Stop button not working
- Hard refresh browser: `Ctrl + Shift + R`
- Check Console (F12) for errors
- Verify sessionId is present in logs

---

## 📝 Technical Stack

**Backend:**
- FastAPI - Async web framework
- Uvicorn - ASGI server
- WebSockets - Real-time communication
- Threading - Multi-worker cookie checking

**Frontend (Integrated):**
- Next.js 13+ - React framework
- TailwindCSS - Styling
- Lucide Icons - UI icons
- WebSocket API - Real-time updates

---

## 🔐 Security Notes

- Service runs on localhost by default
- For production, use reverse proxy (nginx/caddy)
- Enable HTTPS for production deployment
- Secure WebSocket (WSS) for encrypted connection
- Keep output files secure

---

## ⚠️ Disclaimer

**Educational use only.**  
Use only on accounts and cookies you are authorized to test.  
Do not share valid results publicly.

---

## 📚 Additional Documentation

Moved to `scripts/webchecker/`:
- **main.py** - Standalone CLI checker (3489 lines)
- **start_webapp.bat** - Windows launcher script
- **sample_cookies.txt** - Example cookie file

---

## 🙏 Credits

- Original Checker: [harshitkamboj](https://github.com/harshitkamboj)
- WebApp Integration: Enhanced with FastAPI + WebSocket
- Ucok Store Integration: 2026-07

---

## 📄 License

MIT License. See `LICENSE` file.

---

## 🔗 Links

- **Project:** Ucok Store - Telegram Bot + Admin Panel
- **Main Launcher:** `run_complete.py` (project root)
- **Admin Panel:** http://localhost:3000
- **API Docs:** http://localhost:8001/docs (when running)

---

**Last Updated:** 2026-07-12
