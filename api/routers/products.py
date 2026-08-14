from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_api_key
from api.database import get_connection
from api.models import ProductOut, ProductCreate, ProductUpdate, VariantOut, VariantCreate, VariantUpdate, StockItemOut
from api.stock_manager import count_stok_file_lines, count_folder_files, STOCK_SOURCE_FILE_LINES, STOCK_SOURCE_FOLDER_FILES

router = APIRouter(prefix="/products", tags=["products"])


def _get_available_stock(conn, product_id: int, variant_id: int = 0, stock_source: str = "database", stock_config: str = "") -> int:
    if stock_source == STOCK_SOURCE_FILE_LINES:
        return count_stok_file_lines(stock_config) if stock_config else 0
    if stock_source == STOCK_SOURCE_FOLDER_FILES:
        return count_folder_files(stock_config) if stock_config else 0
    return conn.execute(
        "SELECT COUNT(*) FROM product_stock WHERE product_id=? AND variant_id=? AND status='available'",
        (product_id, variant_id),
    ).fetchone()[0]


def _has_variants(conn, product_id: int) -> bool:
    return conn.execute(
        "SELECT COUNT(*) FROM product_variants WHERE product_id=?", (product_id,)
    ).fetchone()[0] > 0


def _row_to_product(conn, r) -> ProductOut:
    pid = r["id"]
    has_v = _has_variants(conn, pid)
    src = r["stock_source"] if "stock_source" in r.keys() else "database"
    cfg = r["stock_config"] if "stock_config" in r.keys() else ""
    stock = _get_available_stock(conn, pid, 0, src, cfg) if not has_v else 0
    return ProductOut(
        product_id=pid,
        name=r["name"],
        category=r["category"],
        price=r["price"],
        description=r["description"],
        available_stock=stock,
        custom_id=r["custom_id"],
        has_variants=has_v,
        is_active=bool(r["is_active"]),
        stock_source=src,
        stock_config=cfg,
    )


def _row_to_variant(conn, r, product_id: int) -> VariantOut:
    src = r["stock_source"] if "stock_source" in r.keys() else "database"
    cfg = r["stock_config"] if "stock_config" in r.keys() else ""
    stock = _get_available_stock(conn, product_id, r["id"], src, cfg)
    return VariantOut(
        variant_id=r["id"],
        product_id=r["product_id"],
        name=r["name"],
        price=r["price"],
        custom_id=r["custom_id"],
        available_stock=stock,
        stock_source=src,
        stock_config=cfg,
    )


@router.get("", response_model=list[ProductOut])
def list_products(active_only: bool = False, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        query = "SELECT * FROM products"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY id DESC"
        rows = conn.execute(query).fetchall()
        return [_row_to_product(conn, r) for r in rows]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        r = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
        return _row_to_product(conn, r)


@router.post("", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO products (name, category, price, description, custom_id, stock_source, stock_config) VALUES (?,?,?,?,?,?,?)",
            (data.name, data.category, data.price, data.description, data.custom_id, data.stock_source, data.stock_config),
        )
        product_id = cur.lastrowid
        conn.commit()
    return get_product(product_id, api_key)


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, api_key: str = Depends(get_api_key)):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Tidak ada field yang diupdate")
    if "is_active" in fields:
        fields["is_active"] = 1 if fields["is_active"] else 0
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE products SET {set_clause} WHERE id=?",
            (*fields.values(), product_id),
        )
        conn.commit()
    return get_product(product_id, api_key)


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()


@router.get("/{product_id}/variants", response_model=list[VariantOut])
def list_variants(product_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM product_variants WHERE product_id=? ORDER BY id", (product_id,)
        ).fetchall()
        return [_row_to_variant(conn, r, product_id) for r in rows]


@router.get("/{product_id}/stock", response_model=list[StockItemOut])
def list_stock(product_id: int, status: str = "available", api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM product_stock WHERE product_id=? AND status=? ORDER BY id",
            (product_id, status),
        ).fetchall()
    return [
        StockItemOut(
            stock_id=r["id"],
            product_id=r["product_id"],
            variant_id=r["variant_id"],
            content=r["content"],
            status=r["status"],
            delivered_to_user_id=r["delivered_to_user_id"],
            delivered_at=r["delivered_at"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/{product_id}/variants", response_model=VariantOut, status_code=201)
def create_variant(product_id: int, data: VariantCreate, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        product = conn.execute("SELECT id FROM products WHERE id=?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Produk tidak ditemukan")
        cur = conn.execute(
            "INSERT INTO product_variants (product_id, name, price, custom_id, stock_source, stock_config) VALUES (?,?,?,?,?,?)",
            (product_id, data.name, data.price, data.custom_id, data.stock_source, data.stock_config),
        )
        variant_id = cur.lastrowid
        conn.commit()
        r = conn.execute("SELECT * FROM product_variants WHERE id=?", (variant_id,)).fetchone()
        return _row_to_variant(conn, r, product_id)


@router.patch("/{product_id}/variants/{variant_id}", response_model=VariantOut)
def update_variant(product_id: int, variant_id: int, data: VariantUpdate, api_key: str = Depends(get_api_key)):
    fields = {k: v for k, v in data.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="Tidak ada field yang diupdate")
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with get_connection() as conn:
        conn.execute(
            f"UPDATE product_variants SET {set_clause} WHERE id=? AND product_id=?",
            (*fields.values(), variant_id, product_id),
        )
        conn.commit()
        r = conn.execute("SELECT * FROM product_variants WHERE id=?", (variant_id,)).fetchone()
        if not r:
            raise HTTPException(status_code=404, detail="Varian tidak ditemukan")
        return _row_to_variant(conn, r, product_id)


@router.delete("/{product_id}/variants/{variant_id}", status_code=204)
def delete_variant(product_id: int, variant_id: int, api_key: str = Depends(get_api_key)):
    with get_connection() as conn:
        conn.execute("DELETE FROM product_variants WHERE id=? AND product_id=?", (variant_id, product_id))
        conn.commit()
