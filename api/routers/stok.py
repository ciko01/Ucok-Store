from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.auth import get_api_key
from api.database import get_connection
from api.stock_manager import (
    list_stok_files,
    list_stok_folders,
    count_stok_file_lines,
    count_folder_files,
    STOCK_SOURCE_DATABASE,
    STOCK_SOURCE_FILE_LINES,
    STOCK_SOURCE_FOLDER_FILES,
)

router = APIRouter(prefix="/stok", tags=["stok"])


class StokFileInfo(BaseModel):
    filename: str
    path: str
    size_bytes: int
    lines: int


class StokFolderInfo(BaseModel):
    foldername: str
    file_count: int


class StockSourceUpdate(BaseModel):
    stock_source: str
    stock_config: str = ""


@router.get("/files", response_model=list[StokFileInfo])
def list_files(api_key: str = Depends(get_api_key)):
    return [StokFileInfo(**f) for f in list_stok_files()]


@router.get("/folders", response_model=list[StokFolderInfo])
def list_folders(api_key: str = Depends(get_api_key)):
    return [StokFolderInfo(**f) for f in list_stok_folders()]


@router.get("/files/{filename}/preview")
def preview_file(filename: str, limit: int = 10, api_key: str = Depends(get_api_key)):
    from api.stock_manager import get_stok_file_lines
    lines = get_stok_file_lines(filename)
    return {
        "filename": filename,
        "total_lines": len(lines),
        "preview": lines[:limit],
    }


@router.put("/products/{product_id}/source")
def set_product_stock_source(product_id: int, data: StockSourceUpdate, api_key: str = Depends(get_api_key)):
    if data.stock_source not in (STOCK_SOURCE_DATABASE, STOCK_SOURCE_FILE_LINES, STOCK_SOURCE_FOLDER_FILES):
        raise HTTPException(status_code=400, detail="stock_source tidak valid")
    with get_connection() as conn:
        p = conn.execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
        conn.execute(
            "UPDATE products SET stock_source=?, stock_config=? WHERE id=?",
            (data.stock_source, data.stock_config, product_id),
        )
        conn.commit()
        row = conn.execute("SELECT stock_source, stock_config FROM products WHERE id=?", (product_id,)).fetchone()
    return {"product_id": product_id, "stock_source": row["stock_source"], "stock_config": row["stock_config"]}


@router.put("/variants/{variant_id}/source")
def set_variant_stock_source(variant_id: int, data: StockSourceUpdate, api_key: str = Depends(get_api_key)):
    if data.stock_source not in (STOCK_SOURCE_DATABASE, STOCK_SOURCE_FILE_LINES, STOCK_SOURCE_FOLDER_FILES):
        raise HTTPException(status_code=400, detail="stock_source tidak valid")
    with get_connection() as conn:
        v = conn.execute("SELECT id FROM product_variants WHERE id=?", (variant_id,)).fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Varian tidak ditemukan")
        conn.execute(
            "UPDATE product_variants SET stock_source=?, stock_config=? WHERE id=?",
            (data.stock_source, data.stock_config, variant_id),
        )
        conn.commit()
        row = conn.execute("SELECT stock_source, stock_config FROM product_variants WHERE id=?", (variant_id,)).fetchone()
    return {"variant_id": variant_id, "stock_source": row["stock_source"], "stock_config": row["stock_config"]}


@router.get("/products/{product_id}/source")
def get_product_stock_source(product_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT stock_source, stock_config FROM products WHERE id=?", (product_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
    return {"product_id": product_id, "stock_source": row["stock_source"] or "database", "stock_config": row["stock_config"] or ""}


@router.get("/variants/{variant_id}/source")
def get_variant_stock_source(variant_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT stock_source, stock_config FROM product_variants WHERE id=?", (variant_id,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Varian tidak ditemukan")
    return {"variant_id": variant_id, "stock_source": row["stock_source"] or "database", "stock_config": row["stock_config"] or ""}
