"""
Script untuk menjalankan Bot Telegram + API + Webapp + Web Checker dalam 1 terminal
"""
import asyncio
import threading
import subprocess
import sys
import os
import time
from pathlib import Path
import uvicorn
from telegram_bot.app import build_application
from api.bot_instance import set_bot


def run_api():
    """Jalankan FastAPI di thread terpisah"""
    print("🚀 Starting API server...")
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=False)


def run_webchecker():
    """Jalankan Web Checker FastAPI di subprocess"""
    webchecker_dir = Path(__file__).parent / "scripts" / "webchecker"

    print("🔍 Starting Web Checker server...")

    # Jalankan webchecker sebagai subprocess (seperti webapp)
    webchecker_process = subprocess.Popen(
        "python -m uvicorn app:app --host 0.0.0.0 --port 8001",
        cwd=webchecker_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        shell=True
    )

    # Print output dari webchecker
    for line in iter(webchecker_process.stdout.readline, ''):
        if line:
            print(f"[WebChecker] {line.rstrip()}")

    webchecker_process.wait()


def run_webapp():
    """Jalankan Next.js webapp di subprocess"""
    webapp_dir = Path(__file__).parent / "webapp"

    print("🌐 Starting Next.js webapp...")

    # Jalankan webapp (development mode - tidak butuh build)
    webapp_process = subprocess.Popen(
        "npm run dev",
        cwd=webapp_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        shell=True  # Penting untuk Windows
    )

    # Print output dari webapp
    for line in iter(webapp_process.stdout.readline, ''):
        if line:
            print(f"[Webapp] {line.rstrip()}")

    webapp_process.wait()


async def run_bot():
    """Jalankan Telegram bot"""
    print("🤖 Starting Telegram bot...")
    app = build_application()
    await app.initialize()
    await app.start()
    loop = asyncio.get_event_loop()
    set_bot(app.bot, loop)
    await app.updater.start_polling()
    print("✅ Bot berjalan. Tekan Ctrl+C untuk berhenti.")
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


def main():
    print("=" * 70)
    print("🎯 UCOK STORE - COMPLETE LAUNCHER")
    print("=" * 70)
    print()
    print("Menjalankan 4 komponen:")
    print("  1. 🤖 Bot Telegram")
    print("  2. 🚀 FastAPI (http://localhost:8000)")
    print("  3. 🔍 Web Checker (http://localhost:8001)")
    print("  4. 🌐 Webapp (http://localhost:3000)")
    print()
    print("=" * 70)
    print()

    # Jalankan API di thread terpisah
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    print("✅ API server started at http://localhost:8000")

    # Beri waktu API untuk start
    time.sleep(2)

    # Jalankan Web Checker di thread terpisah
    webchecker_thread = threading.Thread(target=run_webchecker, daemon=True)
    webchecker_thread.start()
    print("✅ Web Checker server started at http://localhost:8001")

    # Beri waktu webchecker untuk start
    time.sleep(2)

    # Jalankan webapp di thread terpisah
    webapp_thread = threading.Thread(target=run_webapp, daemon=True)
    webapp_thread.start()
    print("✅ Webapp starting at http://localhost:3000")

    # Beri waktu webapp untuk start
    time.sleep(3)

    print()
    print("=" * 70)
    print("🎉 Semua komponen sudah berjalan!")
    print()
    print("📍 URL Penting:")
    print("   • Admin Panel: http://localhost:3000")
    print("   • API Docs:    http://localhost:8000/docs")
    print("   • Web Checker: http://localhost:8001")
    print()
    print("💡 Tips:")
    print("   • Akses admin panel di http://localhost:3000")
    print("   • Tekan Ctrl+C untuk menghentikan semua")
    print("=" * 70)
    print()

    # Jalankan bot di main thread (blocking)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n\n👋 Menghentikan semua komponen...")
        print("✅ Selesai!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Dihentikan oleh user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
