from __future__ import annotations

import io
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.auth import get_api_key

router = APIRouter(prefix="/filemanager", tags=["filemanager"])

STOK_DIR = Path(__file__).parent.parent.parent / "stok"


def _resolve(rel: str) -> Path:
    """Resolve path relatif ke STOK_DIR, cegah path traversal."""
    STOK_DIR.mkdir(parents=True, exist_ok=True)
    target = (STOK_DIR / rel.lstrip("/")).resolve()
    if not str(target).startswith(str(STOK_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Path tidak diizinkan")
    return target


def _entry(path: Path, base: Path) -> dict:
    stat = path.stat()
    rel = str(path.relative_to(base)).replace("\\", "/")
    return {
        "name": path.name,
        "path": rel,
        "is_dir": path.is_dir(),
        "size": stat.st_size if path.is_file() else None,
        "modified": stat.st_mtime,
    }


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("/list")
def list_dir(path: str = "", api_key: str = Depends(get_api_key)):
    target = _resolve(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Bukan folder")
    entries = sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    return {
        "path": path.lstrip("/"),
        "entries": [_entry(e, STOK_DIR) for e in entries],
    }


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_files(
    path: str = Form(""),
    files: list[UploadFile] = File(...),
    api_key: str = Depends(get_api_key),
):
    target_dir = _resolve(path)
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in files:
        dest = target_dir / f.filename
        content = await f.read()
        dest.write_bytes(content)
        saved.append(f.filename)
    return {"uploaded": saved}


# ── Delete ────────────────────────────────────────────────────────────────────

class DeleteRequest(BaseModel):
    paths: list[str]


@router.post("/delete")
def delete_items(data: DeleteRequest, api_key: str = Depends(get_api_key)):
    deleted = []
    for p in data.paths:
        target = _resolve(p)
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        deleted.append(p)
    return {"deleted": deleted}


# ── Create ────────────────────────────────────────────────────────────────────

class CreateRequest(BaseModel):
    path: str
    name: str
    kind: str  # "file" | "folder"
    content: str = ""


@router.post("/create")
def create_item(data: CreateRequest, api_key: str = Depends(get_api_key)):
    target = _resolve(f"{data.path}/{data.name}")
    if target.exists():
        raise HTTPException(status_code=400, detail="Sudah ada")
    if data.kind == "folder":
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data.content, encoding="utf-8")
    return {"created": str(target.relative_to(STOK_DIR)).replace("\\", "/")}


# ── Rename ────────────────────────────────────────────────────────────────────

class RenameRequest(BaseModel):
    path: str
    new_name: str


@router.post("/rename")
def rename_item(data: RenameRequest, api_key: str = Depends(get_api_key)):
    src = _resolve(data.path)
    if not src.exists():
        raise HTTPException(status_code=404, detail="Tidak ditemukan")
    dest = src.parent / data.new_name
    if dest.exists():
        raise HTTPException(status_code=400, detail="Nama sudah dipakai")
    src.rename(dest)
    return {"renamed": str(dest.relative_to(STOK_DIR)).replace("\\", "/")}


# ── Copy / Move ───────────────────────────────────────────────────────────────

class CopyMoveRequest(BaseModel):
    sources: list[str]
    destination: str
    operation: str  # "copy" | "move"


@router.post("/copy-move")
def copy_move(data: CopyMoveRequest, api_key: str = Depends(get_api_key)):
    dest_dir = _resolve(data.destination)
    dest_dir.mkdir(parents=True, exist_ok=True)
    done = []
    for src_rel in data.sources:
        src = _resolve(src_rel)
        if not src.exists():
            continue
        dest = dest_dir / src.name
        if dest.exists():
            base, ext = os.path.splitext(src.name)
            dest = dest_dir / f"{base}_copy{ext}"
        if data.operation == "copy":
            if src.is_dir():
                shutil.copytree(src, dest)
            else:
                shutil.copy2(src, dest)
        else:
            shutil.move(str(src), dest)
        done.append(src.name)
    return {"operation": data.operation, "done": done}


# ── Zip ───────────────────────────────────────────────────────────────────────

class ZipRequest(BaseModel):
    paths: list[str]
    zip_name: str
    destination: str = ""


@router.post("/zip")
def zip_items(data: ZipRequest, api_key: str = Depends(get_api_key)):
    zip_name = data.zip_name if data.zip_name.endswith(".zip") else f"{data.zip_name}.zip"
    dest_dir = _resolve(data.destination) if data.destination else STOK_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in data.paths:
            src = _resolve(p)
            if src.is_dir():
                for f in src.rglob("*"):
                    if f.is_file():
                        zf.write(f, f.relative_to(src.parent))
            elif src.is_file():
                zf.write(src, src.name)
    return {"zip": str(zip_path.relative_to(STOK_DIR)).replace("\\", "/")}


# ── Unzip ─────────────────────────────────────────────────────────────────────

class UnzipRequest(BaseModel):
    path: str
    destination: str = ""


@router.post("/unzip")
def unzip_item(data: UnzipRequest, api_key: str = Depends(get_api_key)):
    src = _resolve(data.path)
    if not src.exists() or not src.is_file():
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    dest_dir = _resolve(data.destination) if data.destination else src.parent / src.stem
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dest_dir)
    return {"extracted_to": str(dest_dir.relative_to(STOK_DIR)).replace("\\", "/")}


# ── Download ──────────────────────────────────────────────────────────────────

@router.get("/download")
def download_file(path: str, api_key: str = Depends(get_api_key)):
    target = _resolve(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    if target.is_dir():
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in target.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(target.parent))
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={target.name}.zip"},
        )
    return StreamingResponse(
        iter([target.read_bytes()]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={target.name}"},
    )


# ── Read file content ─────────────────────────────────────────────────────────

@router.get("/read")
def read_file(path: str, api_key: str = Depends(get_api_key)):
    target = _resolve(path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File tidak ditemukan")
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="File tidak bisa dibaca sebagai teks")
    return {"path": path, "content": content, "size": target.stat().st_size}


# ── Write file content ────────────────────────────────────────────────────────

class WriteRequest(BaseModel):
    path: str
    content: str


@router.post("/write")
def write_file(data: WriteRequest, api_key: str = Depends(get_api_key)):
    target = _resolve(data.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(data.content, encoding="utf-8")
    return {"path": data.path, "size": target.stat().st_size}
