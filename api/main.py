from __future__ import annotations

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from api.routers.products import router as products_router
from api.routers.users import router as users_router
from api.routers.transactions import router as transactions_router
from api.routers.topup import router as topup_router
from api.routers.banks import router as banks_router
from api.routers.stats import router as stats_router
from api.routers.settings import router as settings_router, logs_router
from api.routers.auth import router as auth_router, init_admin_table
from api.routers.broadcast import router as broadcast_router
from api.routers.stok import router as stok_router
from api.routers.filemanager import router as filemanager_router
from api.routers.membership import router as membership_router
from api.routers.vouchers import router as vouchers_router
from api.routers.web_checker import router as web_checker_router

app = FastAPI(
    title="Ucok Store API",
    description="REST API untuk Ucok Store – terhubung dengan Telegram Bot",
    version="1.0.0",
)

webapp_origin = os.getenv("WEBAPP_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[webapp_origin, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(topup_router, prefix="/api")
app.include_router(banks_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
app.include_router(broadcast_router, prefix="/api")
app.include_router(stok_router, prefix="/api")
app.include_router(filemanager_router, prefix="/api")
app.include_router(membership_router, prefix="/api")
app.include_router(vouchers_router, prefix="/api")
app.include_router(web_checker_router, prefix="/api")

@app.on_event("startup")
def on_startup():
    init_admin_table()

@app.get("/api/health")
def health():
    return {"status": "ok"}
