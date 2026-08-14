"""
Web Checker Router - Netflix Cookie Validation API
Integrated from webchecker/app.py into main Ucok Store API
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
import json
import zipfile
import io
import queue
import threading
import sys
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

# Global state untuk tracking checking sessions
checking_sessions: Dict[str, "CheckerSession"] = {}

router = APIRouter(prefix="/web-checker", tags=["web-checker"])


class CheckerSession:
    """Session untuk tracking progress cookie checking"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.total = 0
        self.checked = 0
        self.valid = 0
        self.invalid = 0
        self.broken = 0
        self.duplicate = 0
        self.on_hold = 0
        self.organized = 0
        self.dead = 0
        self.status = "pending"  # pending, running, complete
        self.results = {
            "premium": [], "premium_extra": [], "standard": [],
            "standard_with_ads": [], "basic": [], "mobile": [],
            "free": [], "on_hold": [], "unknown": [], "duplicate": [],
        }
        self.is_running = False
        self.websocket_clients: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message ke semua connected WebSocket clients"""
        async with self._lock:
            clients = list(self.websocket_clients)

        dead = []
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"[BROADCAST] Failed to send to client: {e}")
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.websocket_clients:
                        self.websocket_clients.remove(ws)

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress statistics"""
        return {
            "total": self.total,
            "checked": self.checked,
            "valid": self.valid,
            "invalid": self.invalid,
            "broken": self.broken,
            "duplicate": self.duplicate,
            "on_hold": self.on_hold,
            "progress": self.checked / self.total if self.total > 0 else 0,
        }


@router.post("/check")
async def start_check(files: List[UploadFile] = File(...)):
    """Upload multiple cookie files (txt/json/zip) dan start checking"""

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # For now, return a simple response indicating checking would start
    # Full implementation would require webchecker functions
    session = CheckerSession(session_id)
    session.total = 0
    checking_sessions[session_id] = session

    file_count = 0
    for file in files:
        raw = await file.read()
        fname = (file.filename or "").lower()

        # Count files processed
        if fname.endswith((".txt", ".json", ".zip")):
            file_count += 1

    return {
        "session_id": session_id,
        "total_cookies": file_count,
        "file_count": file_count,
        "message": f"Web Checker endpoint is available. Uploaded {file_count} file(s)"
    }


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint untuk real-time progress updates"""
    await websocket.accept()

    session = checking_sessions.get(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    async with session._lock:
        session.websocket_clients.append(websocket)

    try:
        # Send initial progress
        await websocket.send_json({
            "type": "progress",
            "data": session.get_progress()
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        async with session._lock:
            if websocket in session.websocket_clients:
                session.websocket_clients.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        async with session._lock:
            if websocket in session.websocket_clients:
                session.websocket_clients.remove(websocket)


@router.get("/session/{session_id}")
def get_session_status(session_id: str):
    """Get status dari checking session"""
    session = checking_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "status": "running" if session.is_running else "complete",
        "progress": session.get_progress(),
        "results": session.results,
    }


@router.post("/check/single")
async def single_check(request: dict):
    """Check a single cookie string"""
    cookie_text = request.get("cookie", "").strip()
    if not cookie_text:
        raise HTTPException(status_code=400, detail="No cookie provided")

    # Placeholder response
    return {
        "success": False,
        "reason": "web_checker_integration_in_progress",
        "message": "Web Checker integration is in progress. Full functionality coming soon."
    }


@router.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "web-checker"}


# ══════════════════════════════════════════════════════════════════════
#  CLEANUP ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

# Cookie extraction & validation utilities
PROJECT_ROOT = Path(__file__).parent.parent.parent
COOKIES_DIR = PROJECT_ROOT / "stok" / "netflix"
REQUEST_TIMEOUT = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

def extract_cookies_from_netscape(text: str) -> Optional[Dict[str, str]]:
    """Extract cookies dari format Netscape"""
    cookies = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            parts = re.split(r"\s+", line, maxsplit=6)
        if len(parts) >= 7:
            name = parts[5].strip()
            value = parts[6].strip()
            if name in ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent"):
                cookies[name] = value
    return cookies if "NetflixId" in cookies else None

def extract_cookies_from_json(text: str) -> Optional[Dict[str, str]]:
    """Extract cookies dari format JSON"""
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("cookies") or data.get("items") or [data]
        if not isinstance(data, list):
            return None
        cookies = {}
        for cookie in data:
            if not isinstance(cookie, dict):
                continue
            name = cookie.get("name", "").strip()
            value = cookie.get("value", "").strip()
            if name in ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent"):
                cookies[name] = value
        return cookies if "NetflixId" in cookies else None
    except (json.JSONDecodeError, Exception):
        return None

def extract_cookies_from_file(filepath: Path) -> Optional[Dict[str, str]]:
    """Extract cookies dari file (auto-detect format)"""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
        if filepath.suffix.lower() == ".json":
            cookies = extract_cookies_from_json(content)
            if cookies:
                return cookies
        cookies = extract_cookies_from_netscape(content)
        if cookies:
            return cookies
        cookies = extract_cookies_from_json(content)
        return cookies
    except Exception as e:
        print(f"[ERROR] Gagal extract cookies dari {filepath}: {e}")
        return None

def validate_cookie(cookies: Dict[str, str], proxy: Optional[Dict] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validasi cookie via Netflix API. Returns: (is_valid, country, plan)"""
    session = requests.Session()
    session.cookies.update(cookies)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = session.get(
            "https://www.netflix.com/account/membership",
            headers=headers,
            proxies=proxy,
            timeout=REQUEST_TIMEOUT,
            verify=False,
        )
        if response.status_code != 200:
            return False, None, None
        text = response.text
        country_match = re.search(r'"currentCountry"\s*:\s*"([^"]+)"', text)
        if not country_match:
            country_match = re.search(r'"countryOfSignup":\s*"([^"]+)"', text)
        if not country_match:
            return False, None, None
        country = country_match.group(1)
        plan_match = re.search(r'"localizedPlanName"\s*:\s*"([^"]+)"', text)
        plan = plan_match.group(1) if plan_match else "Unknown"
        plan_lower = plan.lower()
        if "premium" in plan_lower:
            plan = "Premium"
        elif "standard" in plan_lower:
            plan = "Standard"
        elif "basic" in plan_lower:
            plan = "Basic"
        elif "mobile" in plan_lower:
            plan = "Mobile"
        return True, country, plan
    except Exception as e:
        print(f"[DEBUG] Validation error: {e}")
        return False, None, None


@router.post("/cleanup")
async def start_cleanup():
    """
    Cleanup cookies: scan stok/netflix/, validate, organize by Country/Plan, delete dead
    """
    if not COOKIES_DIR.exists():
        raise HTTPException(status_code=404, detail=f"Directory {COOKIES_DIR} not found")
    
    # Collect cookie files (only root level)
    cookie_files = []
    for ext in [".txt", ".json"]:
        for filepath in COOKIES_DIR.glob(f"*{ext}"):
            if filepath.parent == COOKIES_DIR:
                cookie_files.append(filepath)
    
    if not cookie_files:
        raise HTTPException(status_code=400, detail="No cookie files found")
    
    session_id = f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    session = CheckerSession(session_id)
    session.total = len(cookie_files)
    session.status = "pending"
    checking_sessions[session_id] = session
    
    # Start cleanup in background
    asyncio.create_task(run_cleanup_task(session_id, cookie_files))
    
    return {
        "session_id": session_id,
        "total_cookies": len(cookie_files),
        "message": f"Cleanup started: checking {len(cookie_files)} cookies"
    }


async def run_cleanup_task(session_id: str, cookie_files: List[Path]):
    """Run cleanup task in background with progress broadcast"""
    session = checking_sessions.get(session_id)
    if not session:
        return
    
    session.is_running = True
    session.status = "running"
    
    # Worker queue
    result_queue = queue.Queue()
    task_queue = queue.Queue()
    
    for idx, filepath in enumerate(cookie_files):
        task_queue.put((idx, filepath))
    
    NUM_WORKERS = 10
    
    def worker():
        """Worker thread untuk check cookies"""
        thread_id = threading.get_ident()
        
        while True:
            try:
                item = task_queue.get(timeout=2)
            except queue.Empty:
                break
            
            if item is None:
                task_queue.task_done()
                break
            
            idx, filepath = item
            
            try:
                print(f"[CLEANUP-WORKER-{thread_id}] Checking cookie {idx+1}/{session.total}")
                
                # Extract cookies
                cookies = extract_cookies_from_file(filepath)
                if not cookies:
                    print(f"[CLEANUP-WORKER-{thread_id}] Cookie {idx+1} invalid (no cookies)")
                    result_queue.put(("dead", filepath, None, None))
                    task_queue.task_done()
                    continue
                
                # Validate
                is_valid, country, plan = validate_cookie(cookies)
                
                if not is_valid:
                    print(f"[CLEANUP-WORKER-{thread_id}] Cookie {idx+1} DEAD")
                    result_queue.put(("dead", filepath, None, None))
                else:
                    print(f"[CLEANUP-WORKER-{thread_id}] Cookie {idx+1} VALID: {country}/{plan}")
                    result_queue.put(("valid", filepath, country, plan))
                
            except Exception as e:
                print(f"[CLEANUP-WORKER-{thread_id}] Error checking cookie {idx+1}: {e}")
                result_queue.put(("dead", filepath, None, None))
            finally:
                task_queue.task_done()
    
    # Start workers
    workers = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        workers.append(t)
    
    # Process results
    checked = 0
    valid_results = []  # (filepath, country, plan)
    dead_files = []
    
    loop = asyncio.get_event_loop()
    
    def get_result():
        try:
            return result_queue.get(timeout=1)
        except queue.Empty:
            return None
    
    while checked < session.total:
        result = await loop.run_in_executor(None, get_result)
        
        if result is None:
            # Check if workers still alive
            alive = sum(1 for t in workers if t.is_alive())
            if alive == 0 and result_queue.empty():
                break
            continue
        
        status, filepath, country, plan = result
        checked += 1
        
        if status == "valid":
            session.valid += 1
            valid_results.append((filepath, country, plan))
        else:
            session.dead += 1
            dead_files.append(filepath)
        
        session.checked = checked
        percentage = int((checked / session.total) * 100)
        
        # Broadcast progress
        await session.broadcast({
            "type": "progress",
            "data": {
                "checked": checked,
                "total": session.total,
                "valid": session.valid,
                "dead": session.dead,
                "percentage": percentage
            }
        })
    
    # Wait for workers
    for t in workers:
        t.join(timeout=5)
    
    print(f"[CLEANUP] Check complete: {session.valid} valid, {session.dead} dead")
    
    # Organize valid cookies
    organized_count = 0
    successfully_organized = set()
    
    for filepath, country, plan in valid_results:
        try:
            output_dir = COOKIES_DIR / country / plan
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / filepath.name
            counter = 1
            while output_path.exists():
                output_path = output_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
                counter += 1
            
            # Copy file
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            output_path.write_text(content, encoding="utf-8")
            
            if output_path.exists() and output_path.stat().st_size > 0:
                successfully_organized.add(str(filepath))
                organized_count += 1
                print(f"[CLEANUP] Organized: {filepath.name} -> {country}/{plan}/")
        except Exception as e:
            print(f"[CLEANUP] Error organizing {filepath}: {e}")
    
    # Delete dead files
    for filepath in dead_files:
        try:
            if str(filepath) not in successfully_organized:
                filepath.unlink()
                print(f"[CLEANUP] Deleted dead file: {filepath.name}")
        except Exception as e:
            print(f"[CLEANUP] Error deleting {filepath}: {e}")
    
    # Delete successfully organized files from root
    for filepath_str in successfully_organized:
        try:
            filepath = Path(filepath_str)
            if filepath.exists():
                filepath.unlink()
                print(f"[CLEANUP] Deleted organized file: {filepath.name}")
        except Exception as e:
            print(f"[CLEANUP] Error deleting organized file: {e}")
    
    session.organized = organized_count
    session.status = "complete"
    session.is_running = False
    
    # Final broadcast
    await session.broadcast({
        "type": "complete",
        "data": {
            "total": session.total,
            "valid": session.valid,
            "dead": session.dead,
            "organized": organized_count
        }
    })
    
    print(f"[CLEANUP] Session {session_id} complete")


@router.get("/session/{session_id}/progress")
async def get_cleanup_progress(session_id: str):
    """Get cleanup progress"""
    session = checking_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "status": session.status,
        "total": session.total,
        "checked": session.checked,
        "valid": session.valid,
        "dead": session.dead,
        "organized": session.organized,
        "percentage": int((session.checked / session.total) * 100) if session.total > 0 else 0,
    }


# Keep original CheckerSession for backward compatibility below
class CheckerSession:
    """Session untuk tracking progress cookie checking"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.total = 0
        self.checked = 0
        self.valid = 0
        self.invalid = 0
        self.broken = 0
        self.duplicate = 0
        self.on_hold = 0
        self.organized = 0
        self.dead = 0
        self.status = "pending"  # pending, running, complete
        self.results = {
            "premium": [], "premium_extra": [], "standard": [],
            "standard_with_ads": [], "basic": [], "mobile": [],
            "free": [], "on_hold": [], "unknown": [], "duplicate": [],
        }
        self.is_running = False
        self.websocket_clients: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message ke semua connected WebSocket clients"""
        async with self._lock:
            clients = list(self.websocket_clients)

        dead = []
        for ws in clients:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"[BROADCAST] Failed to send to client: {e}")
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.websocket_clients:
                        self.websocket_clients.remove(ws)

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress statistics"""
        return {
            "total": self.total,
            "checked": self.checked,
            "valid": self.valid,
            "invalid": self.invalid,
            "broken": self.broken,
            "duplicate": self.duplicate,
            "on_hold": self.on_hold,
            "progress": self.checked / self.total if self.total > 0 else 0,
        }


@router.post("/check")
async def start_check(files: List[UploadFile] = File(...)):
    """Upload multiple cookie files (txt/json/zip) dan start checking"""

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    all_bundles = []
    file_count = 0

    for file in files:
        raw = await file.read()
        fname = (file.filename or "").lower()

        # Handle ZIP files
        if fname.endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    for name in zf.namelist():
                        if name.lower().endswith((".txt", ".json")) and not name.startswith("__"):
                            try:
                                text = zf.read(name).decode("utf-8", errors="ignore")
                                bundles = extract_netflix_cookie_bundles(text)
                                all_bundles.extend(bundles)
                                if bundles:
                                    file_count += 1
                            except Exception:
                                continue
            except zipfile.BadZipFile:
                continue
        else:
            # Handle txt/json files
            text = raw.decode("utf-8", errors="ignore")
            bundles = extract_netflix_cookie_bundles(text)
            all_bundles.extend(bundles)
            if bundles:
                file_count += 1

    if not all_bundles:
        raise HTTPException(status_code=400, detail="No valid Netflix cookies found in uploaded files")

    session = CheckerSession(session_id)
    session.total = len(all_bundles)
    checking_sessions[session_id] = session

    config_result = load_config()
    config = config_result[0] if isinstance(config_result, tuple) else config_result
    if config is None:
        config = DEFAULT_CONFIG

    # Start checker task asynchronously
    asyncio.create_task(run_checker(session_id, all_bundles, config))

    return {
        "session_id": session_id,
        "total_cookies": len(all_bundles),
        "file_count": file_count,
        "message": f"Checking {len(all_bundles)} cookies from {file_count} file(s)"
    }


async def run_checker(session_id: str, cookie_bundles: List[Dict[str, Any]], config: Dict):
    """Run cookie checker dalam background"""
    session = checking_sessions.get(session_id)
    if not session:
        return

    session.is_running = True
    seen_cookies = set()
    seen_lock = threading.Lock()
    proxies = load_proxies()

    result_queue: queue.Queue = queue.Queue()
    NUM_WORKERS = 5  # Reduced from 10 untuk safety

    print(f"[CHECKER] Starting run_checker for session {session_id} with {len(cookie_bundles)} cookies")

    def worker():
        thread_id = threading.get_ident()
        tasks_processed = 0

        while True:
            try:
                item = task_queue.get(timeout=2)
            except queue.Empty:
                if task_queue.unfinished_tasks == 0:
                    break
                continue

            if item is None:
                task_queue.task_done()
                break

            bundle, idx = item
            try:
                print(f"[WORKER-{thread_id}] Processing cookie {idx+1}/{len(cookie_bundles)}")
                cookie_dict = bundle.get("cookies", {})
                cookie_text = bundle.get("netscape_text", "")

                if not has_required_netflix_cookies(cookie_dict):
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} invalid (missing required cookies)")
                    result_queue.put({"type": "invalid", "cookie_text": cookie_text})
                    continue

                cookie_str = json.dumps(cookie_dict, sort_keys=True)
                with seen_lock:
                    if cookie_str in seen_cookies:
                        print(f"[WORKER-{thread_id}] Cookie {idx+1} duplicate")
                        result_queue.put({"type": "duplicate", "cookie_text": cookie_text})
                        continue
                    seen_cookies.add(cookie_str)

                print(f"[WORKER-{thread_id}] Checking cookie {idx+1} with Netflix...")

                check_timeout = config.get("retries", {}).get("error_proxy_attempts", 3) * \
                               (config.get("performance", {}).get("request_timeout_seconds", 15) + 10)

                check_executor = ThreadPoolExecutor(max_workers=1)
                future = check_executor.submit(check_single_cookie, cookie_dict, cookie_text, proxies, config)

                try:
                    result = future.result(timeout=check_timeout)
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} check completed successfully")
                except FuturesTimeoutError:
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} check TIMEOUT")
                    future.cancel()
                    result = {"success": False, "reason": "timeout"}
                except Exception as check_exc:
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} check EXCEPTION: {check_exc}")
                    future.cancel()
                    result = {"success": False, "reason": "error"}
                finally:
                    check_executor.shutdown(wait=False)

                if result.get("success"):
                    info = result["info"]
                    is_subscribed = is_subscribed_account(info)
                    plan_key, plan_display = derive_plan_info(info, is_subscribed)
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} valid: {plan_display}")

                    if is_extra_member_account(info) and plan_key == "premium":
                        plan_category = "premium_extra"
                    elif is_on_hold_account(info):
                        plan_category = "on_hold"
                    else:
                        plan_category = plan_key

                    nftoken_data = None
                    nftoken_mode = get_nftoken_mode(config)
                    if nftoken_mode and (is_subscribed or config.get("performance", {}).get("nftoken_for_free", False)):
                        try:
                            nftoken_attempts = config.get("retries", {}).get("nftoken_attempts", 1)
                            r = create_nftoken(cookie_dict, nftoken_attempts)
                            nftoken_data = r[0] if isinstance(r, tuple) else r
                        except Exception as e:
                            print(f"[WORKER-{thread_id}] NFToken error for cookie {idx+1}: {e}")

                    use_emojis = should_add_emojis(config, "txt")
                    detail_lines = build_account_detail_lines(
                        config, info, is_subscribed,
                        output_filename=None, use_emojis=use_emojis, include_country_flag=True
                    )
                    cookie_content = format_cookie_file(info, cookie_text, config, is_subscribed, nftoken_data)

                    result_queue.put({
                        "type": "valid",
                        "plan": plan_display,
                        "plan_category": plan_category,
                        "on_hold": plan_category == "on_hold",
                        "account": {
                            "cookie": cookie_text,
                            "info": info,
                            "plan": plan_display,
                            "formatted": "\n".join(detail_lines),
                            "cookie_content": cookie_content,
                            "nftoken": nftoken_data
                        }
                    })
                elif result.get("reason") == "retryable":
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} broken (retryable error)")
                    result_queue.put({"type": "broken", "cookie_text": cookie_text})
                else:
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} invalid: {result.get('reason', 'unknown')}")
                    result_queue.put({"type": "invalid", "cookie_text": cookie_text})

            except Exception as e:
                print(f"[WORKER-{thread_id}] FATAL Exception processing cookie {idx+1}: {e}")
                result_queue.put({"type": "broken", "cookie_text": bundle.get("netscape_text", "")})

            finally:
                task_queue.task_done()
                tasks_processed += 1

        print(f"[WORKER-{thread_id}] Thread exiting, total processed: {tasks_processed}")

    # Fill task queue
    task_queue: queue.Queue = queue.Queue()
    for i, bundle in enumerate(cookie_bundles):
        task_queue.put((bundle, i))

    print(f"[CHECKER] Added {len(cookie_bundles)} tasks to queue")

    # Start worker threads
    threads = []
    for wid in range(NUM_WORKERS):
        t = threading.Thread(target=worker, daemon=True, name=f"Worker-{wid}")
        t.start()
        threads.append(t)

    print(f"[CHECKER] Started {NUM_WORKERS} worker threads")

    # Async loop: read results
    loop = asyncio.get_event_loop()
    completed = 0
    total = len(cookie_bundles)
    no_result_count = 0
    MAX_NO_RESULT_ITERATIONS = 300

    def get_result_nonblocking():
        try:
            return result_queue.get(timeout=1)
        except queue.Empty:
            return None

    print(f"[CHECKER] Starting result collection loop")

    while completed < total:
        if not session.is_running:
            print(f"[CHECKER] Session stopped by user at {completed}/{total}")
            break

        res = await loop.run_in_executor(None, get_result_nonblocking)

        if res is None:
            no_result_count += 1

            alive = sum(1 for t in threads if t.is_alive())
            queue_size = task_queue.qsize()
            unfinished = task_queue.unfinished_tasks

            if no_result_count % 10 == 0:
                print(f"[CHECKER] Waiting... completed={completed}/{total}, alive_workers={alive}")

            if alive == 0 and result_queue.empty():
                print(f"[CHECKER] All workers dead and result queue empty at {completed}/{total}")
                break

            if no_result_count > MAX_NO_RESULT_ITERATIONS:
                print(f"[CHECKER] Timeout: no results for {MAX_NO_RESULT_ITERATIONS} seconds")
                break

            continue

        no_result_count = 0
        completed += 1
        rtype = res.get("type")

        print(f"[CHECKER] Got result {completed}/{total}: type={rtype}")

        if rtype == "valid":
            session.valid += 1
            session.checked += 1
            if res["on_hold"]:
                session.on_hold += 1
            cat = res["plan_category"]
            session.results.setdefault(cat, []).append(res["account"])
            await session.broadcast({
                "type": "valid_account",
                "data": {"plan": res["plan"], "category": cat, "account": res["account"]}
            })
        elif rtype == "duplicate":
            session.duplicate += 1
            session.checked += 1
        elif rtype == "broken":
            session.broken += 1
            session.checked += 1
        else:
            session.invalid += 1
            session.checked += 1

        await session.broadcast({"type": "progress", "data": session.get_progress()})

    session.is_running = False
    await session.broadcast({"type": "complete", "data": session.get_progress()})


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint untuk real-time progress updates"""
    await websocket.accept()

    session = checking_sessions.get(session_id)
    if not session:
        await websocket.close(code=1008, reason="Session not found")
        return

    async with session._lock:
        session.websocket_clients.append(websocket)

    try:
        # Send initial progress
        await websocket.send_json({
            "type": "progress",
            "data": session.get_progress()
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Echo atau handle commands jika diperlukan
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        async with session._lock:
            if websocket in session.websocket_clients:
                session.websocket_clients.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        async with session._lock:
            if websocket in session.websocket_clients:
                session.websocket_clients.remove(websocket)


@router.get("/session/{session_id}")
def get_session_status(session_id: str):
    """Get status dari checking session"""
    session = checking_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "status": "running" if session.is_running else "complete",
        "progress": session.get_progress(),
        "results": session.results,
    }


@router.post("/check/single")
async def single_check(request: dict):
    """Check a single cookie string"""
    cookie_text = request.get("cookie", "").strip()
    if not cookie_text:
        raise HTTPException(status_code=400, detail="No cookie provided")

    bundles = extract_netflix_cookie_bundles(cookie_text)
    if not bundles:
        raise HTTPException(status_code=400, detail="No valid Netflix cookies found")

    bundle = bundles[0]
    cookie_dict = bundle.get("cookies", {})
    netscape_text = bundle.get("netscape_text", "")

    if not has_required_netflix_cookies(cookie_dict):
        raise HTTPException(status_code=400, detail="Missing required Netflix cookies")

    config_result = load_config()
    config = config_result[0] if isinstance(config_result, tuple) else config_result
    if config is None:
        config = DEFAULT_CONFIG

    proxies = load_proxies()
    result = await asyncio.to_thread(check_single_cookie, cookie_dict, netscape_text, proxies, config)

    if not result.get("success"):
        return {"success": False, "reason": result.get("reason", "failed")}

    info = result["info"]
    is_subscribed = is_subscribed_account(info)
    plan_key, plan_display = derive_plan_info(info, is_subscribed)

    if is_extra_member_account(info) and plan_key == "premium":
        plan_key = "premium_extra"
        plan_display = "Premium (Extra Member)"
    on_hold = is_on_hold_account(info)

    nftoken_data = None
    nftoken_mode = get_nftoken_mode(config)
    if nftoken_mode and (is_subscribed or config.get("performance", {}).get("nftoken_for_free", False)):
        try:
            nftoken_attempts = config.get("retries", {}).get("nftoken_attempts", 1)
            result = await asyncio.to_thread(create_nftoken, cookie_dict, nftoken_attempts)
            nftoken_data = result[0] if isinstance(result, tuple) else result
        except Exception:
            pass

    use_emojis = should_add_emojis(config, "txt")
    detail_lines = build_account_detail_lines(config, info, is_subscribed, output_filename=None, use_emojis=use_emojis, include_country_flag=True)
    formatted = "\n".join(detail_lines)
    cookie_content = format_cookie_file(info, netscape_text, config, is_subscribed, nftoken_data)

    return {
        "success": True,
        "plan": plan_display,
        "plan_key": plan_key,
        "on_hold": on_hold,
        "is_subscribed": is_subscribed,
        "info": info,
        "formatted": formatted,
        "cookie_content": cookie_content,
        "nftoken": nftoken_data,
        "netscape_text": netscape_text,
    }
