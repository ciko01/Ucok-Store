from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import zipfile
import io
import queue
import threading
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import List, Dict, Any
import tempfile
from pathlib import Path

# Import fungsi-fungsi dari main.py
from main import (
    load_config,
    extract_netflix_cookie_bundles,
    cookies_dict_from_netscape,
    has_required_netflix_cookies,
    derive_plan_info,
    is_extra_member_account,
    is_on_hold_account,
    create_nftoken,
    build_account_detail_lines,
    format_cookie_file,
    get_nftoken_mode,
    should_add_emojis,
    is_subscribed_account,
    load_proxies,
    get_account_page,
    extract_info,
    has_complete_account_info,
    DEFAULT_CONFIG,
)

import requests

app = FastAPI(title="Netflix Cookie Checker WebApp", version="4.5")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state untuk tracking progress
checking_sessions = {}


class CheckerSession:
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
        self.status = "pending"  # pending, running, complete
        self.results = {
            "premium": [], "premium_extra": [], "standard": [],
            "standard_with_ads": [], "basic": [], "mobile": [],
            "free": [], "on_hold": [], "unknown": [], "duplicate": [],
        }
        self.is_running = False
        self.websocket_clients = []
        self._lock = asyncio.Lock()

    async def broadcast(self, message: Dict[str, Any]):
        async with self._lock:
            clients = list(self.websocket_clients)
        print(f"[BROADCAST] Sending {message.get('type')} to {len(clients)} clients")
        
        # Sanitize message to prevent UTF-8 surrogate errors
        sanitized = self._sanitize_for_json(message)
        
        dead = []
        for ws in clients:
            try:
                await ws.send_json(sanitized)
                print(f"[BROADCAST] Successfully sent to client")
            except Exception as e:
                print(f"[BROADCAST] Failed to send to client: {e}")
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self.websocket_clients:
                        self.websocket_clients.remove(ws)
            print(f"[BROADCAST] Removed {len(dead)} dead clients")
    
    def _sanitize_for_json(self, obj):
        """Recursively sanitize object to remove UTF-8 surrogates and invalid characters"""
        if isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._sanitize_for_json(item) for item in obj]
        elif isinstance(obj, str):
            # Remove surrogates and encode/decode to ensure valid UTF-8
            return obj.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        else:
            return obj

    def get_progress(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total": self.total,
            "checked": self.checked,
            "valid": self.valid,
            "invalid": self.invalid,
            "dead": self.invalid,  # Alias for cleanup context
            "broken": self.broken,
            "duplicate": self.duplicate,
            "on_hold": self.on_hold,
            "organized": self.organized,
            "status": self.status,
            "percentage": int((self.checked / self.total * 100) if self.total > 0 else 0),
            "is_running": self.is_running,
        }

    def get_results_summary(self) -> Dict[str, Any]:
        return {k: len(v) for k, v in self.results.items()}


def check_single_cookie(cookie_dict: Dict, cookie_text: str, proxies: List, config: Dict) -> Dict:
    """Check a single Netflix cookie using same logic as main.py"""
    thread_id = threading.get_ident()
    
    retries_cfg = config.get("retries", {})
    performance_cfg = config.get("performance", {})
    max_retry_attempts = max(1, int(retries_cfg.get("error_proxy_attempts", 3)))
    request_timeout_seconds = max(5, int(performance_cfg.get("request_timeout_seconds", 15)))
    fallback_account_page = bool(performance_cfg.get("fallback_account_page", False))
    retry_incomplete_info = bool(performance_cfg.get("retry_incomplete_info", False))
    retryable_status_codes = {403, 429, 500, 502, 503, 504}
    
    # Global timeout: max_retry_attempts * (timeout + 5s overhead per attempt)
    global_timeout = max_retry_attempts * (request_timeout_seconds + 5)

    session = requests.Session()
    session.cookies.update(cookie_dict)

    used_proxy_indices = set()
    response_text = None
    status_code = None
    extracted_info = None
    last_exception = None

    def get_next_proxy():
        if not proxies:
            return None
        available = [i for i in range(len(proxies)) if i not in used_proxy_indices]
        if not available:
            available = list(range(len(proxies)))
        idx = random.choice(available)
        used_proxy_indices.add(idx)
        return proxies[idx]

    for attempt in range(max_retry_attempts):
        proxy = get_next_proxy()
        start_time = time.time()  # Define BEFORE try block
        try:
            print(f"[API-{thread_id}] Attempt {attempt+1}/{max_retry_attempts}, calling Netflix API...")
            
            response_text, status_code, extracted_info = get_account_page(
                session,
                proxy,
                request_timeout=request_timeout_seconds,
                fallback_account_page=fallback_account_page,
            )
            
            elapsed = time.time() - start_time
            print(f"[API-{thread_id}] Netflix API responded in {elapsed:.2f}s, status={status_code}")
            
            if status_code == 200 and response_text:
                if retry_incomplete_info and attempt < max_retry_attempts - 1:
                    if not (extracted_info and has_complete_account_info(extracted_info)):
                        print(f"[API-{thread_id}] Incomplete info, retrying...")
                        continue
                break
            if status_code in retryable_status_codes and attempt < max_retry_attempts - 1:
                print(f"[API-{thread_id}] Retryable status {status_code}, retrying...")
                continue
            break
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[API-{thread_id}] Exception after {elapsed:.2f}s: {type(e).__name__}: {e}")
            last_exception = e
            if attempt < max_retry_attempts - 1:
                print(f"[API-{thread_id}] Retrying after exception...")
                continue

    if status_code == 200 and response_text:
        info = extracted_info or extract_info(response_text)
        if info.get("countryOfSignup") and info.get("countryOfSignup") != "null":
            print(f"[API-{thread_id}] Success: valid account")
            return {"success": True, "info": info}
        else:
            print(f"[API-{thread_id}] Failed: incomplete info")
            return {"success": False, "reason": "incomplete_info"}
    elif last_exception is not None or status_code in retryable_status_codes:
        print(f"[API-{thread_id}] Failed: retryable")
        return {"success": False, "reason": "retryable"}
    else:
        print(f"[API-{thread_id}] Failed: final status {status_code}")
        return {"success": False, "reason": "failed"}


@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")


@app.post("/api/check/single")
async def single_check(request: Request):
    """Check a single cookie string (JSON or Netscape text)"""
    body = await request.json()
    cookie_text = body.get("cookie", "").strip()
    if not cookie_text:
        raise HTTPException(status_code=400, detail="No cookie provided")

    bundles = extract_netflix_cookie_bundles(cookie_text)
    if not bundles:
        raise HTTPException(status_code=400, detail="No valid Netflix cookies found")

    bundle = bundles[0]
    cookie_dict = bundle.get("cookies", {})
    netscape_text = bundle.get("netscape_text", "")

    if not has_required_netflix_cookies(cookie_dict):
        raise HTTPException(status_code=400, detail="Missing required Netflix cookies (NetflixId, SecureNetflixId)")

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


@app.post("/api/check")
async def start_check(files: List[UploadFile] = File(...)):
    """Upload multiple cookie files (txt/json/zip) and start checking"""

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

    asyncio.create_task(run_checker(session_id, all_bundles, config))

    return {
        "session_id": session_id,
        "total_cookies": len(all_bundles),
        "file_count": file_count,
        "message": f"Checking {len(all_bundles)} cookies from {file_count} file(s)"
    }


async def run_checker(session_id: str, cookie_bundles: List[Dict[str, Any]], config: Dict):
    session = checking_sessions.get(session_id)
    if not session:
        return

    session.is_running = True
    seen_cookies = set()
    seen_lock = threading.Lock()
    proxies = load_proxies()

    # Result queue — worker threads push results, async loop reads them
    result_queue: queue.Queue = queue.Queue()
    NUM_WORKERS = 10
    
    print(f"[CHECKER] Starting run_checker for session {session_id} with {len(cookie_bundles)} cookies")

    def worker():
        thread_id = threading.get_ident()
        print(f"[WORKER-{thread_id}] Thread started")
        tasks_processed = 0
        
        while True:
            # Check if session was stopped by user
            if not session.is_running:
                print(f"[WORKER-{thread_id}] Session stopped by user, exiting. Processed: {tasks_processed}")
                break
                
            try:
                item = task_queue.get(timeout=2)
            except queue.Empty:
                print(f"[WORKER-{thread_id}] Queue empty, checking if done...")
                # Check if we should exit
                if task_queue.unfinished_tasks == 0:
                    print(f"[WORKER-{thread_id}] No more tasks, exiting. Processed: {tasks_processed}")
                    break
                continue
                
            if item is None:
                print(f"[WORKER-{thread_id}] Got poison pill, exiting. Processed: {tasks_processed}")
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
                
                # Wrap dengan timeout protection menggunakan ThreadPoolExecutor
                check_timeout = config.get("retries", {}).get("error_proxy_attempts", 3) * \
                               (config.get("performance", {}).get("request_timeout_seconds", 15) + 10)
                
                check_executor = ThreadPoolExecutor(max_workers=1)
                future = check_executor.submit(check_single_cookie, cookie_dict, cookie_text, proxies, config)
                
                try:
                    result = future.result(timeout=check_timeout)
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} check completed successfully")
                except FuturesTimeoutError:
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} check TIMEOUT after {check_timeout}s")
                    future.cancel()
                    result = {"success": False, "reason": "timeout"}
                except Exception as check_exc:
                    print(f"[WORKER-{thread_id}] Cookie {idx+1} check EXCEPTION: {type(check_exc).__name__}: {check_exc}")
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
                print(f"[WORKER-{thread_id}] FATAL Exception processing cookie {idx+1}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                result_queue.put({"type": "broken", "cookie_text": bundle.get("netscape_text", "")})
            
            finally:
                # ALWAYS call task_done, even if exception
                task_queue.task_done()
                tasks_processed += 1
                print(f"[WORKER-{thread_id}] Completed cookie {idx+1}, total processed: {tasks_processed}")
            
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

    # Async loop: read results without blocking event loop
    loop = asyncio.get_event_loop()
    completed = 0
    total = len(cookie_bundles)
    no_result_count = 0
    MAX_NO_RESULT_ITERATIONS = 300  # 300 seconds = 5 minutes timeout

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
            
            # Check worker status
            alive = sum(1 for t in threads if t.is_alive())
            queue_size = task_queue.qsize()
            unfinished = task_queue.unfinished_tasks
            
            if no_result_count % 10 == 0:  # Log every 10 seconds
                print(f"[CHECKER] Waiting for results... completed={completed}/{total}, alive_workers={alive}, queue_size={queue_size}, unfinished_tasks={unfinished}, result_queue_size={result_queue.qsize()}")
            
            # If all workers dead and no results, break
            if alive == 0 and result_queue.empty():
                print(f"[CHECKER] All workers dead and result queue empty at {completed}/{total}")
                break
            
            # Timeout safety: if no results for too long, break
            if no_result_count > MAX_NO_RESULT_ITERATIONS:
                print(f"[CHECKER] Timeout: no results for {MAX_NO_RESULT_ITERATIONS} seconds at {completed}/{total}")
                break
                
            continue

        # Got a result, reset no_result counter
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

    print(f"[CHECKER] Result collection loop finished: {completed}/{total} completed")

    # Signal workers to stop and wait
    print(f"[CHECKER] Sending poison pills to workers")
    for _ in threads:
        task_queue.put(None)
    
    print(f"[CHECKER] Waiting for workers to finish...")
    for t in threads:
        t.join(timeout=5)
    
    alive_after = sum(1 for t in threads if t.is_alive())
    if alive_after > 0:
        print(f"[CHECKER] Warning: {alive_after} workers still alive after join timeout")

    session.is_running = False
    print(f"[CHECKER] Session complete: {session.get_progress()}")
    
    await session.broadcast({
        "type": "complete",
        "data": {"progress": session.get_progress(), "summary": session.get_results_summary()}
    })


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates"""
    print(f"[WS] New WebSocket connection request for session {session_id}")
    await websocket.accept()
    print(f"[WS] WebSocket accepted")
    
    session = checking_sessions.get(session_id)
    if not session:
        print(f"[WS] Session {session_id} not found")
        await websocket.send_json({
            "type": "error",
            "message": "Session not found"
        })
        await websocket.close()
        return
    
    # Add client to session
    async with session._lock:
        session.websocket_clients.append(websocket)
        client_count = len(session.websocket_clients)
    print(f"[WS] Client added to session {session_id}, total clients: {client_count}")
    
    # Send initial progress
    initial_progress = session.get_progress()
    print(f"[WS] Sending initial progress: {initial_progress}")
    await websocket.send_json({
        "type": "progress",
        "data": initial_progress
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except Exception as e:
        print(f"[WS] WebSocket exception: {type(e).__name__}: {e}")
    finally:
        async with session._lock:
            if websocket in session.websocket_clients:
                session.websocket_clients.remove(websocket)
                client_count = len(session.websocket_clients)
        print(f"[WS] Client disconnected from session {session_id}, remaining clients: {client_count}")


@app.get("/api/session/{session_id}/progress")
async def get_progress(session_id: str):
    """Get current progress of a checking session"""
    session = checking_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.get_progress()


@app.get("/api/session/{session_id}/results")
async def get_results(session_id: str):
    """Get results of a checking session"""
    session = checking_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "progress": session.get_progress(),
        "summary": session.get_results_summary(),
        "results": session.results
    }


@app.get("/api/session/{session_id}/download/{category}")
async def download_results(session_id: str, category: str):
    """Download results as text file"""
    session = checking_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if category not in session.results:
        raise HTTPException(status_code=404, detail="Category not found")
    
    accounts = session.results[category]
    
    if not accounts:
        raise HTTPException(status_code=404, detail="No accounts in this category")
    
    # Create output directory
    output_dir = f"output/run_{session_id}/{category}"
    os.makedirs(output_dir, exist_ok=True)
    
    # Write to file
    output_file = os.path.join(output_dir, f"{category}.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for account in accounts:
            f.write(account.get("cookie_content", "") + "\n\n")
            f.write("="*70 + "\n\n")
    
    return FileResponse(
        output_file,
        filename=f"{category}_{session_id}.txt",
        media_type="text/plain"
    )


@app.post("/api/session/{session_id}/stop")
async def stop_checking(session_id: str):
    """Stop a running checking session"""
    session = checking_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_running = False
    
    await session.broadcast({
        "type": "stopped",
        "message": "Checking stopped by user"
    })
    
    return {"message": "Checking stopped"}


@app.post("/api/cleanup")
async def start_cleanup():
    """
    Cleanup cookies from stok/netflix/:
    - Scan all cookies in stok/netflix/
    - Check validity using Web Checker
    - Delete dead cookies
    - Move valid cookies to stok/netflix/{Country}/{Plan}/
    """
    
    # Input directory
    input_dir = Path("../../stok/netflix")
    if not input_dir.exists():
        raise HTTPException(status_code=404, detail="Input directory stok/netflix/ not found")
    
    # Collect all cookie files
    cookie_files = list(input_dir.glob("*.txt")) + list(input_dir.glob("*.json"))
    # Exclude files already in subdirectories
    cookie_files = [f for f in cookie_files if f.parent == input_dir]
    
    if not cookie_files:
        raise HTTPException(status_code=400, detail="No cookie files found in stok/netflix/")
    
    session_id = f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Extract bundles from all files
    all_bundles = []
    file_map = {}  # Map bundle index to original file
    
    for filepath in cookie_files:
        try:
            text = filepath.read_text(encoding="utf-8", errors="ignore")
            bundles = extract_netflix_cookie_bundles(text)
            
            for bundle in bundles:
                bundle['_source_file'] = str(filepath)
                all_bundles.append(bundle)
                file_map[len(all_bundles) - 1] = filepath
                
        except Exception as e:
            print(f"[CLEANUP] Error reading {filepath}: {e}")
            continue
    
    if not all_bundles:
        raise HTTPException(status_code=400, detail="No valid cookies found in files")
    
    session = CheckerSession(session_id)
    session.total = len(all_bundles)
    checking_sessions[session_id] = session
    
    config_result = load_config()
    config = config_result[0] if isinstance(config_result, tuple) else config_result
    if config is None:
        config = DEFAULT_CONFIG
    
    # Start cleanup task
    asyncio.create_task(run_cleanup(session_id, all_bundles, file_map, input_dir, config))
    
    return {
        "session_id": session_id,
        "total_cookies": len(all_bundles),
        "total_files": len(cookie_files),
        "message": f"Cleanup started: checking {len(all_bundles)} cookies from {len(cookie_files)} files"
    }


async def run_cleanup(session_id: str, cookie_bundles: List[Dict[str, Any]], file_map: Dict, input_dir: Path, config: Dict):
    """Run cleanup: check cookies, organize by Country/Plan, delete dead"""
    session = checking_sessions.get(session_id)
    if not session:
        return
    
    # Wait for WebSocket clients to connect (with timeout)
    print(f"[CLEANUP] Waiting for WebSocket clients to connect...")
    max_wait = 10  # Maximum 10 seconds (increased for bot connection time)
    waited = 0
    while waited < max_wait:
        async with session._lock:
            client_count = len(session.websocket_clients)
        if client_count > 0:
            print(f"[CLEANUP] {client_count} client(s) connected, starting cleanup...")
            break
        await asyncio.sleep(0.5)
        waited += 0.5
    
    async with session._lock:
        final_count = len(session.websocket_clients)
    if final_count == 0:
        print(f"[CLEANUP] No clients connected after {max_wait}s, proceeding anyway...")
    
    session.is_running = True
    session.status = "running"
    proxies = load_proxies()
    
    result_queue: queue.Queue = queue.Queue()
    NUM_WORKERS = 10
    
    print(f"[CLEANUP] Starting cleanup for session {session_id} with {len(cookie_bundles)} cookies")
    
    # Track results
    valid_cookies = []  # List of (bundle, country, plan, source_file)
    dead_files = set()  # Files to delete
    
    def worker():
        thread_id = threading.get_ident()
        
        while True:
            if not session.is_running:
                print(f"[CLEANUP-WORKER-{thread_id}] Session stopped")
                break
            
            try:
                item = task_queue.get(timeout=2)
            except queue.Empty:
                if task_queue.unfinished_tasks == 0:
                    break
                continue
            
            if item is None:
                task_queue.task_done()
                break
            
            idx, bundle = item
            source_file = bundle.get('_source_file', '')
            
            try:
                cookies_dict = cookies_dict_from_netscape(bundle['netscape_text'])
                if not has_required_netflix_cookies(cookies_dict):
                    print(f"[CLEANUP-WORKER-{thread_id}] Cookie {idx} missing required fields")
                    result_queue.put(('dead', idx, source_file))
                    continue
                
                # Validate cookie
                proxy = proxies[idx % len(proxies)] if proxies else None
                print(f"[CLEANUP-WORKER-{thread_id}] Checking cookie {idx} with proxy: {proxy}")
                
                # Add delay for progress visibility (2s per cookie untuk 10 workers = ~20s per batch)
                import time
                time.sleep(2.0)
                
                # Create requests session with cookies
                req_session = requests.Session()
                req_session.cookies.update(cookies_dict)
                
                response_text, status_code, extracted_info = get_account_page(
                    req_session,
                    proxy,
                    request_timeout=20,
                    fallback_account_page=False
                )
                
                if status_code != 200 or not response_text:
                    print(f"[CLEANUP-WORKER-{thread_id}] Cookie {idx} failed to get account page (status={status_code})")
                    result_queue.put(('dead', idx, source_file))
                    continue
                
                # Extract info
                info = extracted_info or extract_info(response_text)
                if not has_complete_account_info(info):
                    print(f"[CLEANUP-WORKER-{thread_id}] Cookie {idx} incomplete account info")
                    result_queue.put(('dead', idx, source_file))
                    continue
                
                # Valid cookie - get country and plan
                country = info.get('countryOfSignup', 'Unknown')
                is_subscribed = info.get('isSubscribed', False)
                plan_tier, plan_display = derive_plan_info(info, is_subscribed)
                plan = plan_tier or 'Unknown'
                
                print(f"[CLEANUP-WORKER-{thread_id}] Cookie {idx} VALID: {country}/{plan}")
                result_queue.put(('valid', idx, source_file, country, plan, bundle))
                
            except Exception as e:
                import traceback
                print(f"[CLEANUP-WORKER-{thread_id}] Error checking cookie {idx}: {e}")
                print(f"[CLEANUP-WORKER-{thread_id}] Traceback: {traceback.format_exc()}")
                result_queue.put(('dead', idx, source_file))
            finally:
                task_queue.task_done()
    
    # Start workers
    task_queue = queue.Queue()
    for idx, bundle in enumerate(cookie_bundles):
        task_queue.put((idx, bundle))
    
    # Poison pills
    for _ in range(NUM_WORKERS):
        task_queue.put(None)
    
    workers = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        workers.append(t)
    
    # Process results
    checked = 0
    valid_count = 0
    dead_count = 0
    
    while checked < len(cookie_bundles):
        try:
            result = result_queue.get(timeout=1)
            
            if result[0] == 'valid':
                _, idx, source_file, country, plan, bundle = result
                valid_cookies.append((bundle, country, plan, source_file))
                valid_count += 1
            else:  # dead
                _, idx, source_file = result
                dead_files.add(source_file)
                dead_count += 1
            
            checked += 1
            percentage = int((checked / len(cookie_bundles)) * 100)
            
            # Update session state
            session.checked = checked
            session.valid = valid_count
            session.invalid = dead_count
            
            await session.broadcast({
                "type": "progress",
                "data": {
                    "percentage": percentage,
                    "checked": checked,
                    "total": len(cookie_bundles),
                    "valid": valid_count,
                    "dead": dead_count
                }
            })
            
        except queue.Empty:
            continue
    
    # Wait for all workers
    for t in workers:
        t.join(timeout=5)
    
    print(f"[CLEANUP] Check complete: {valid_count} valid, {dead_count} dead")
    
    # Organize valid cookies into Country/Plan folders
    organized_count = 0
    successfully_organized = set()  # Track successfully organized files
    
    for bundle, country, plan, source_file in valid_cookies:
        try:
            # Create output directory
            output_dir = input_dir / country / plan
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate output filename
            source_path = Path(source_file)
            output_path = output_dir / source_path.name
            
            # Handle duplicate names
            counter = 1
            while output_path.exists():
                output_path = output_dir / f"{source_path.stem}_{counter}{source_path.suffix}"
                counter += 1
            
            # Write cookie to output
            output_path.write_text(bundle['netscape_text'], encoding='utf-8')
            
            # Verify file was written successfully
            if output_path.exists() and output_path.stat().st_size > 0:
                successfully_organized.add(source_file)
                organized_count += 1
            else:
                print(f"[CLEANUP] WARNING: Failed to verify {output_path}")
            
        except Exception as e:
            print(f"[CLEANUP] Error organizing {source_file}: {e}")
    
    # Delete dead files from input (ONLY dead, not valid)
    deleted_count = 0
    for filepath in dead_files:
        try:
            # Safety check: don't delete if it's in successfully_organized
            if filepath not in successfully_organized:
                Path(filepath).unlink()
                deleted_count += 1
            else:
                print(f"[CLEANUP] Skipping deletion of {filepath} (marked as valid)")
        except Exception as e:
            print(f"[CLEANUP] Error deleting {filepath}: {e}")
    
    # Delete source files that were successfully organized
    for filepath in successfully_organized:
        try:
            source_path = Path(filepath)
            if source_path.exists():
                source_path.unlink()
                print(f"[CLEANUP] Deleted organized file: {filepath}")
        except Exception as e:
            print(f"[CLEANUP] Error deleting organized file {filepath}: {e}")
    
    # Final broadcast
    await session.broadcast({
        "type": "complete",
        "data": {
            "total": len(cookie_bundles),
            "valid": valid_count,
            "dead": dead_count,
            "organized": organized_count,
            "deleted": deleted_count
        }
    })
    
    # Update final session state
    session.status = "complete"
    session.organized = organized_count
    session.is_running = False
    print(f"[CLEANUP] Session {session_id} complete")


# Mount static files
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


if __name__ == "__main__":
    import uvicorn
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    print("="*70)
    print("Netflix Cookie Checker WebApp V4.5")
    print("="*70)
    print()
    print("Server starting at: http://localhost:8000")
    print("Open your browser and navigate to the URL above")
    print()
    print("Press CTRL+C to stop the server")
    print("="*70)
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
