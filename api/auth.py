from __future__ import annotations

import os
from pathlib import Path
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

API_KEY_NAME = "X-API-Key"
_api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def get_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    expected = os.getenv("WEBAPP_API_KEY", "").strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WEBAPP_API_KEY belum dikonfigurasi di .env",
        )
    if api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key tidak valid",
        )
    return api_key
