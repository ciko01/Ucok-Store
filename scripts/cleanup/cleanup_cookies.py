"""
Netflix Cookie Cleanup Script
Standalone script untuk validasi dan organisasi cookies Netflix

Usage:
    python cleanup_cookies.py

Features:
    - Scan cookies di stok/netflix/
    - Validasi via Netflix API
    - Organisir valid cookies ke {Country}/{Plan}/
    - Hapus dead cookies
    - Return statistics
"""

import os
import sys
import json
import random
import re
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════

# Path ke stok netflix (relative to script location)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
COOKIES_DIR = PROJECT_ROOT / "stok" / "netflix"
PROXY_FILE = SCRIPT_DIR / "proxy.txt"

REQUEST_TIMEOUT = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

# ══════════════════════════════════════════════════════════════════════
#  PROXY LOADING
# ══════════════════════════════════════════════════════════════════════

def load_proxies() -> List[Dict[str, str]]:
    """Load proxies dari file proxy.txt"""
    proxies = []
    if not PROXY_FILE.exists():
        return proxies

    for line in PROXY_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Parse proxy format: http://user:pass@host:port or host:port
        if "://" in line:
            proxies.append({"http": line, "https": line})
        elif ":" in line:
            parts = line.split(":")
            if len(parts) == 2:  # host:port
                url = f"http://{line}"
                proxies.append({"http": url, "https": url})
            elif len(parts) == 4:  # user:pass:host:port or host:port:user:pass
                if parts[1].isdigit():  # host:port:user:pass
                    url = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                else:  # user:pass:host:port
                    url = f"http://{parts[0]}:{parts[1]}@{parts[2]}:{parts[3]}"
                proxies.append({"http": url, "https": url})

    return proxies


# ══════════════════════════════════════════════════════════════════════
#  COOKIE EXTRACTION
# ══════════════════════════════════════════════════════════════════════

def extract_cookies_from_netscape(text: str) -> Optional[Dict[str, str]]:
    """Extract cookies dari format Netscape"""
    cookies = {}

    for line in text.splitlines():
        line = line.strip()

        # Skip comments dan empty lines
        if not line or line.startswith("#"):
            continue

        # Parse Netscape format: domain flag path secure expiration name value
        parts = line.split("\t")
        if len(parts) < 7:
            parts = re.split(r"\s+", line, maxsplit=6)

        if len(parts) >= 7:
            name = parts[5].strip()
            value = parts[6].strip()

            # Filter Netflix cookies
            if name in ("NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent"):
                cookies[name] = value

    return cookies if "NetflixId" in cookies else None


def extract_cookies_from_json(text: str) -> Optional[Dict[str, str]]:
    """Extract cookies dari format JSON"""
    try:
        data = json.loads(text)

        # Handle berbagai format JSON
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

        # Try JSON first
        if filepath.suffix.lower() == ".json":
            cookies = extract_cookies_from_json(content)
            if cookies:
                return cookies

        # Try Netscape format
        cookies = extract_cookies_from_netscape(content)
        if cookies:
            return cookies

        # Try JSON as fallback
        cookies = extract_cookies_from_json(content)
        return cookies

    except Exception as e:
        print(f"[ERROR] Gagal extract cookies dari {filepath}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════
#  COOKIE VALIDATION
# ══════════════════════════════════════════════════════════════════════

def validate_cookie(cookies: Dict[str, str], proxy: Optional[Dict] = None) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validasi cookie via Netflix API

    Returns:
        (is_valid, country, plan)
    """
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

        # Extract country
        country_match = re.search(r'"currentCountry"\s*:\s*"([^"]+)"', text)
        if not country_match:
            country_match = re.search(r'"countryOfSignup":\s*"([^"]+)"', text)

        if not country_match:
            return False, None, None

        country = country_match.group(1)

        # Extract plan
        plan_match = re.search(r'"localizedPlanName"\s*:\s*"([^"]+)"', text)
        plan = plan_match.group(1) if plan_match else "Unknown"

        # Simplify plan name
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


# ══════════════════════════════════════════════════════════════════════
#  CLEANUP LOGIC
# ══════════════════════════════════════════════════════════════════════

def cleanup_cookies(progress_callback=None) -> Dict[str, int]:
    """
    Main cleanup function

    Args:
        progress_callback: Optional function(checked, total, valid, dead) untuk tracking progress

    Returns:
        dict: {total, valid, dead, organized, errors}
    """
    if not COOKIES_DIR.exists():
        print(f"[ERROR] Directory tidak ditemukan: {COOKIES_DIR}")
        return {"total": 0, "valid": 0, "dead": 0, "organized": 0, "errors": 1}

    # Collect all cookie files (hanya di root, exclude subdirectories)
    cookie_files = []
    for ext in [".txt", ".json"]:
        for filepath in COOKIES_DIR.glob(f"*{ext}"):
            if filepath.parent == COOKIES_DIR:  # Only root level
                cookie_files.append(filepath)

    if not cookie_files:
        print("[INFO] Tidak ada cookie files ditemukan")
        return {"total": 0, "valid": 0, "dead": 0, "organized": 0, "errors": 0}

    print(f"[INFO] Ditemukan {len(cookie_files)} cookie files")

    # Load proxies
    proxies = load_proxies()
    print(f"[INFO] Loaded {len(proxies)} proxies")

    # Statistics
    stats = {
        "total": len(cookie_files),
        "valid": 0,
        "dead": 0,
        "organized": 0,
        "errors": 0
    }

    checked = 0

    # Process each file
    for filepath in cookie_files:
        checked += 1

        # Progress callback
        if progress_callback:
            progress_callback(checked, stats["total"], stats["valid"], stats["dead"])

        print(f"\n[{checked}/{stats['total']}] Checking: {filepath.name}")

        # Extract cookies
        cookies = extract_cookies_from_file(filepath)
        if not cookies:
            print(f"  → [DEAD] Tidak bisa extract cookies")
            stats["dead"] += 1
            try:
                filepath.unlink()
                print(f"  → [DELETED] {filepath.name}")
            except Exception as e:
                print(f"  → [ERROR] Gagal hapus file: {e}")
                stats["errors"] += 1
            continue

        # Validate cookie
        proxy = random.choice(proxies) if proxies else None
        is_valid, country, plan = validate_cookie(cookies, proxy)

        if not is_valid:
            print(f"  → [DEAD] Cookie tidak valid")
            stats["dead"] += 1
            try:
                filepath.unlink()
                print(f"  → [DELETED] {filepath.name}")
            except Exception as e:
                print(f"  → [ERROR] Gagal hapus file: {e}")
                stats["errors"] += 1
            continue

        # Valid cookie - organize to subdirectory
        print(f"  → [VALID] {country} / {plan}")
        stats["valid"] += 1

        try:
            # Create output directory
            output_dir = COOKIES_DIR / country / plan
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output path
            output_path = output_dir / filepath.name

            # Handle duplicates
            counter = 1
            while output_path.exists():
                output_path = output_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
                counter += 1

            # Move file
            filepath.rename(output_path)
            stats["organized"] += 1
            print(f"  → [ORGANIZED] Moved to {country}/{plan}/")

        except Exception as e:
            print(f"  → [ERROR] Gagal organize file: {e}")
            stats["errors"] += 1

    return stats


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    """Main entry point"""
    print("=" * 70)
    print("Netflix Cookie Cleanup Script")
    print("=" * 70)
    print(f"\nCookies directory: {COOKIES_DIR}")
    print(f"Script started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Run cleanup
    stats = cleanup_cookies()

    # Print results
    print("\n" + "=" * 70)
    print("CLEANUP RESULTS")
    print("=" * 70)
    print(f"📊 Total checked:      {stats['total']}")
    print(f"✅ Valid (organized):  {stats['valid']}")
    print(f"🗑️  Dead (deleted):     {stats['dead']}")
    print(f"📁 Organized:          {stats['organized']}")
    print(f"⚠️  Errors:             {stats['errors']}")
    print("=" * 70)

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
