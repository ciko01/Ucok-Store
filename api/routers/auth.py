from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Header
from fastapi.security import APIKeyHeader
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from api.database import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

SECRET_KEY = os.getenv("WEBAPP_SECRET_KEY", "changeme-set-in-env")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24
COOKIE_NAME = "admin_token"


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminOut(BaseModel):
    admin_id: int
    username: str
    created_at: str


def init_admin_table() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()


def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub", "")
        if not username:
            raise HTTPException(status_code=401, detail="Token tidak valid")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token tidak valid atau kadaluarsa")


def get_current_admin(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Belum login")
    token = authorization.removeprefix("Bearer ").strip()
    return verify_token(token)


@router.post("/login")
def login(data: LoginRequest, response: Response):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash FROM admin_users WHERE username = ?",
            (data.username,),
        ).fetchone()
    if not row or not _verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Username atau password salah")
    token = create_token(row["username"])
    return {"username": row["username"], "token": token}


@router.post("/logout")
def logout(response: Response):
    return {"ok": True}


@router.get("/me", response_model=AdminOut)
def me(username: str = Depends(get_current_admin)):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, created_at FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Admin tidak ditemukan")
    return AdminOut(admin_id=row["id"], username=row["username"], created_at=row["created_at"])


@router.post("/setup", response_model=AdminOut, status_code=201)
def setup_first_admin(data: LoginRequest):
    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
        if count > 0:
            raise HTTPException(status_code=403, detail="Admin sudah ada. Gunakan halaman login.")
        hashed = _hash_password(data.password)
        cur = conn.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
            (data.username, hashed),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, username, created_at FROM admin_users WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return AdminOut(admin_id=row["id"], username=row["username"], created_at=row["created_at"])


@router.post("/admins", response_model=AdminOut, status_code=201)
def create_admin(data: LoginRequest, username: str = Depends(get_current_admin)):
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM admin_users WHERE username = ?", (data.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Username sudah dipakai")
        hashed = _hash_password(data.password)
        cur = conn.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
            (data.username, hashed),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, username, created_at FROM admin_users WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return AdminOut(admin_id=row["id"], username=row["username"], created_at=row["created_at"])
