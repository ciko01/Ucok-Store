"""
Cleanup Handler - Cookie Validation & Organization
Polling-based implementation dengan auto-scheduling support
"""

import asyncio
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.stats import add_admin_log, get_setting, set_setting


async def cleanup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cleanup command untuk validasi dan organisir cookies Netflix."""
    message = update.message
    user = update.effective_user

    # Check admin permission
    settings = context.application.bot_data.get("settings")
    if not settings or user.id not in settings.admin_ids:
        await message.reply_text("⛔ Perintah ini hanya untuk admin.")
        return

    parts = message.text.strip().split(maxsplit=2)
    command = parts[0].lower()

    # /cleanup interval <menit> - set auto-cleanup schedule
    if len(parts) >= 3 and parts[1].lower() == "interval":
        await _cleanup_interval(update, context, parts[2])
        return

    # /cleanup run - execute cleanup
    if len(parts) == 2 and parts[1].lower() == "run":
        await _cleanup_run(update, context)
        return

    # /cleanup - show status
    await _cleanup_status(update, context)


async def _cleanup_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show cleanup status dan interval info."""
    interval_str = get_setting("cleanup_interval_minutes", "0")
    interval_minutes = int(interval_str) if interval_str.isdigit() else 0

    if interval_minutes > 0:
        # Calculate hours and minutes
        hours = interval_minutes // 60
        mins = interval_minutes % 60

        if hours > 0 and mins > 0:
            interval_text = f"{hours}j {mins}m"
        elif hours > 0:
            interval_text = f"{hours}j 0m"
        else:
            interval_text = f"{mins}m"

        status_text = f"🟢 Aktif — setiap {interval_text}"

        # Try to get next run time from job
        next_run = "—"
        jobs = context.job_queue.get_jobs_by_name("cookie_cleanup")
        if jobs:
            job = jobs[0]
            if job.next_t:
                next_run_dt = job.next_t
                next_run = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")

        status_section = (
            f"📊 <b>Status:</b> {status_text}\n"
            f"⏰ <b>Next run:</b> {next_run}"
        )
    else:
        status_section = "📊 <b>Status:</b> 🔴 Nonaktif"

    await update.message.reply_text(
        "🧹 <b>Cookie Auto-Cleanup</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{status_section}\n\n"
        "<b>Commands:</b>\n"
        "• <code>/cleanup run</code> — jalankan sekarang\n"
        "• <code>/cleanup interval &lt;menit&gt;</code> — set interval\n"
        "• <code>/cleanup interval 0</code> — matikan auto-cleanup\n\n"
        "<b>Fitur:</b>\n"
        "✅ Validasi cookies via Web Checker\n"
        "✅ Organisir ke folder {Country}/{Plan}/\n"
        "✅ Hapus cookies yang sudah mati\n"
        "✅ Notifikasi otomatis ke admin",
        parse_mode="HTML"
    )


async def _cleanup_interval(update: Update, context: ContextTypes.DEFAULT_TYPE, value: str) -> None:
    """Set atau matikan auto-cleanup interval."""
    user = update.effective_user

    # Validate input
    if not value.isdigit():
        await update.message.reply_text(
            "❌ Error: interval harus berupa angka (dalam menit).\n\n"
            "Contoh:\n"
            "• <code>/cleanup interval 360</code> — setiap 6 jam\n"
            "• <code>/cleanup interval 0</code> — matikan auto-cleanup",
            parse_mode="HTML"
        )
        return

    minutes = int(value)

    if minutes < 0:
        await update.message.reply_text("❌ Error: interval tidak boleh negatif.")
        return

    # Save to database
    set_setting("cleanup_interval_minutes", str(minutes))

    # Reschedule job
    await _schedule_cleanup_job(context.application, minutes)

    # Log to admin
    if minutes > 0:
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0 and mins > 0:
            interval_text = f"{hours}j {mins}m"
        elif hours > 0:
            interval_text = f"{hours}j 0m"
        else:
            interval_text = f"{mins}m"

        add_admin_log(
            user.id,
            f"@{user.username}" if user.username else user.full_name,
            "SET CLEANUP INTERVAL",
            f"interval: {minutes} menit ({interval_text})"
        )

        await update.message.reply_text(
            f"✅ Auto-cleanup diset setiap <b>{interval_text}</b>.\n\n"
            f"Cleanup akan berjalan otomatis dan mengirim notifikasi ke admin.",
            parse_mode="HTML"
        )
    else:
        add_admin_log(
            user.id,
            f"@{user.username}" if user.username else user.full_name,
            "DISABLE CLEANUP INTERVAL",
            "auto-cleanup dimatikan"
        )

        await update.message.reply_text(
            "✅ Auto-cleanup dimatikan.\n\n"
            "Gunakan <code>/cleanup run</code> untuk menjalankan manual.",
            parse_mode="HTML"
        )


async def _schedule_cleanup_job(application, minutes: int) -> None:
    """Schedule atau reschedule cleanup job."""
    job_queue = application.job_queue

    # Remove existing job
    current_jobs = job_queue.get_jobs_by_name("cookie_cleanup")
    for job in current_jobs:
        job.schedule_removal()

    # Add new job if minutes > 0
    if minutes > 0:
        job_queue.run_repeating(
            _cleanup_job,
            interval=minutes * 60,
            first=minutes * 60,
            name="cookie_cleanup"
        )
        print(f"[CLEANUP] Scheduled job every {minutes} minutes")
    else:
        print("[CLEANUP] Auto-cleanup disabled")


async def _cleanup_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job callback untuk auto-cleanup berkala."""
    print("[CLEANUP] Running scheduled cleanup...")

    # Get admin IDs
    settings = context.application.bot_data.get("settings")
    if not settings or not settings.admin_ids:
        print("[CLEANUP] No admin IDs found, skipping scheduled cleanup")
        return

    try:
        # Start cleanup
        response = requests.post(
            "http://localhost:8001/api/cleanup",
            json={},
            timeout=30
        )

        if response.status_code != 200:
            print(f"[CLEANUP] Error: Web Checker returned status {response.status_code}")
            return

        data = response.json()
        session_id = data.get("session_id")
        total_cookies = data.get("total_cookies", 0)

        if not session_id:
            print("[CLEANUP] Error: No session ID from API")
            return

        print(f"[CLEANUP] Started cleanup session {session_id} with {total_cookies} cookies")

        # Poll for progress (with shorter timeout for scheduled job)
        max_polls = 100  # Max 5 minutes (100 * 3s)
        poll_count = 0

        while poll_count < max_polls:
            poll_count += 1
            await asyncio.sleep(3)

            try:
                progress_response = requests.get(
                    f"http://localhost:8001/api/session/{session_id}/progress",
                    timeout=5
                )

                if progress_response.status_code != 200:
                    continue

                progress_data = progress_response.json()
                status = progress_data.get("status", "")

                if status == "complete":
                    total = progress_data.get("total", 0)
                    valid = progress_data.get("valid", 0)
                    dead = progress_data.get("dead", 0)
                    organized = progress_data.get("organized", 0)

                    print(f"[CLEANUP] Job complete: {valid} valid, {dead} dead, {organized} organized")

                    # Notify all admins
                    notification = (
                        "🧹 <b>Auto-Cleanup Selesai</b>\n\n"
                        f"📊 Total dicek: <b>{total}</b>\n"
                        f"✅ Valid (organized): <b>{valid}</b>\n"
                        f"🗑️ Mati (dihapus): <b>{dead}</b>\n\n"
                        f"📁 Cookies valid telah diorganisir ke:\n"
                        f"<code>stok/netflix/{{Country}}/{{Plan}}/</code>\n\n"
                        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )

                    for admin_id in settings.admin_ids:
                        try:
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=notification,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            print(f"[CLEANUP] Failed to notify admin {admin_id}: {e}")

                    return

            except requests.exceptions.RequestException as e:
                print(f"[CLEANUP] Poll error: {e}")
                continue

        print("[CLEANUP] Job timeout after 5 minutes")

    except Exception as e:
        print(f"[CLEANUP] Job error: {e}")


async def _cleanup_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute cleanup with polling-based progress tracking."""
    message = update.message
    user = update.effective_user
    
    # Send initial message
    progress_msg = await message.reply_text(
        "🧹 <b>Cleanup dimulai!</b>\n\n"
        "⏳ Menghubungi Web Checker...",
        parse_mode="HTML"
    )
    
    try:
        # Step 1: POST to start cleanup
        response = requests.post(
            "http://localhost:8001/api/cleanup",
            json={},
            timeout=30
        )
        
        if response.status_code != 200:
            await progress_msg.edit_text(
                f"❌ Error: Web Checker mengembalikan status {response.status_code}"
            )
            return
        
        data = response.json()
        session_id = data.get("session_id")
        total_cookies = data.get("total_cookies", 0)
        
        if not session_id:
            await progress_msg.edit_text("❌ Error: Tidak mendapat session ID dari API")
            return
        
        # Update initial stats
        await progress_msg.edit_text(
            f"🧹 <b>Cleanup dimulai!</b>\n\n"
            f"📊 <b>Total Cookies: {total_cookies}</b>\n"
            f"✅ Aktif: 0\n"
            f"💀 Mati: 0\n"
            f"🌐 Sedang memproses 0/{total_cookies}\n\n"
            f"[░░░░░░░░░░] 0%",
            parse_mode="HTML"
        )
        
        # Step 2: Poll for progress
        last_percentage = 0
        last_checked = 0
        max_polls = 300  # Max 15 menit (300 * 3s)
        poll_count = 0

        while poll_count < max_polls:
            poll_count += 1
            await asyncio.sleep(1)  # Poll setiap 1 detik (lebih cepat)

            try:
                progress_response = requests.get(
                    f"http://localhost:8001/api/session/{session_id}/progress",
                    timeout=15  # Increase timeout to 15 seconds
                )
                
                if progress_response.status_code != 200:
                    continue
                
                progress_data = progress_response.json()
                status = progress_data.get("status", "")
                
                # Check if complete
                if status == "complete":
                    total = progress_data.get("total", 0)
                    valid = progress_data.get("valid", 0)
                    dead = progress_data.get("dead", 0)
                    organized = progress_data.get("organized", 0)
                    
                    # Log to admin
                    add_admin_log(
                        user.id,
                        f"@{user.username}" if user.username else user.full_name,
                        "CLEANUP COOKIES",
                        f"total: {total} | valid: {valid} | dead: {dead} | organized: {organized}"
                    )
                    
                    # Show final result
                    await progress_msg.edit_text(
                        f"✅ <b>Cleanup selesai!</b>\n\n"
                        f"📊 Total dicek: <b>{total}</b>\n"
                        f"✅ Valid (organized): <b>{valid}</b>\n"
                        f"🗑️ Mati (dihapus): <b>{dead}</b>\n\n"
                        f"📁 Cookies valid telah diorganisir ke:\n"
                        f"<code>stok/netflix/{{Country}}/{{Plan}}/</code>",
                        parse_mode="HTML"
                    )
                    return
                
                # Update progress
                checked = progress_data.get("checked", 0)
                valid = progress_data.get("valid", 0)
                dead = progress_data.get("dead", 0)
                percentage = int((checked / total_cookies * 100)) if total_cookies > 0 else 0

                # Update message every 2% OR every 2 cookies checked (lebih sering)
                percentage_delta = percentage - last_percentage
                checked_delta = checked - last_checked

                if percentage_delta >= 2 or checked_delta >= 2:
                    last_percentage = percentage
                    last_checked = checked
                    
                    # Progress bar
                    filled = int(percentage / 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    
                    await progress_msg.edit_text(
                        f"🧹 <b>Cleanup berjalan...</b>\n\n"
                        f"📊 <b>Total Cookies: {total_cookies}</b>\n"
                        f"✅ Aktif: {valid}\n"
                        f"💀 Mati: {dead}\n"
                        f"🌐 Sedang memproses {checked}/{total_cookies}\n\n"
                        f"[{bar}] {percentage}%",
                        parse_mode="HTML"
                    )
            
            except requests.exceptions.RequestException as e:
                print(f"[BOT] Poll error: {e}")
                continue
            except Exception as e:
                print(f"[BOT] Unexpected error during poll: {e}")
                continue
        
        # Timeout after max polls
        await progress_msg.edit_text(
            "⚠️ Cleanup timeout setelah 10 menit.\n"
            "Proses mungkin masih berjalan di background.\n\n"
            "Coba jalankan <code>/cleanup run</code> lagi untuk melihat hasil.",
            parse_mode="HTML"
        )
    
    except requests.exceptions.ConnectionError:
        await progress_msg.edit_text(
            "❌ Error: Web Checker tidak berjalan di port 8001\n\n"
            "Pastikan service Web Checker sudah running."
        )
    except requests.exceptions.Timeout:
        await progress_msg.edit_text(
            "❌ Error: Request timeout\n\n"
            "Web Checker mungkin sedang sibuk atau tidak merespons."
        )
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error: {e}")
        print(f"[BOT] Cleanup error: {e}")
