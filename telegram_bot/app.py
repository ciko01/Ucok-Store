from __future__ import annotations

import re

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from telegram_bot.config import load_settings
from telegram_bot.handlers import (
    addbalance_handler,
    daily_bonus_handler,
    product_callback_handler,
    admin_handler,
    approve_handler,
    broadcast_handler,
    cancel_handler,
    document_handler,
    echo_handler,
    help_handler,
    maintenance_handler,
    myid_handler,
    photo_handler,
    ping_handler,
    reject_handler,
    start_handler,
    stats_handler,
)
from telegram_bot.stats import initialize_database


def build_application() -> Application:
    settings = load_settings()
    initialize_database()
    app = Application.builder().token(settings.bot_token).build()
    app.bot_data["settings"] = settings

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("ping", ping_handler))
    app.add_handler(CommandHandler("admin", admin_handler))
    app.add_handler(CommandHandler("bc", broadcast_handler))
    app.add_handler(CommandHandler("cancel", cancel_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("myid", myid_handler))
    app.add_handler(CommandHandler("addbal", addbalance_handler))
    app.add_handler(CommandHandler("maintenance", maintenance_handler))
    app.add_handler(CommandHandler("bonus", daily_bonus_handler))

    # Dynamic commands: /approve_<id> dan /reject_<id>
    app.add_handler(MessageHandler(
        filters.Regex(re.compile(r"^/approve_\d+$")) & filters.COMMAND,
        approve_handler,
    ))
    app.add_handler(MessageHandler(
        filters.Regex(re.compile(r"^/reject_\d+$")) & filters.COMMAND,
        reject_handler,
    ))

    # Inline keyboard callbacks (katalog, checkout, edit, bonus, soldout)
    app.add_handler(CallbackQueryHandler(
        product_callback_handler,
        pattern=r"^(prod_|checkout_|soldout_|editprod_|editbank_|bonus_)",
    ))

    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, photo_handler))
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, document_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_handler))

    return app


def run() -> None:
    app = build_application()
    print("Bot berjalan. Tekan Ctrl+C untuk berhenti.")
    app.run_polling()
