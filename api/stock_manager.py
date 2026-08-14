from __future__ import annotations

from pathlib import Path
from typing import Optional

STOK_DIR = Path(__file__).parent.parent / "stok"

STOCK_SOURCE_DATABASE = "database"
STOCK_SOURCE_FILE_LINES = "file_lines"
STOCK_SOURCE_FOLDER_FILES = "folder_files"


def _ensure_stok_dir() -> None:
    STOK_DIR.mkdir(parents=True, exist_ok=True)


def list_stok_files() -> list[dict]:
    """List semua file (non-folder) di root folder /stok."""
    _ensure_stok_dir()
    files = []
    for f in sorted(STOK_DIR.iterdir()):
        if f.is_file():
            lines = 0
            try:
                lines = sum(1 for line in f.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())
            except Exception:
                pass
            files.append({
                "filename": f.name,
                "path": str(f.relative_to(STOK_DIR.parent)),
                "size_bytes": f.stat().st_size,
                "lines": lines,
            })
    return files


def list_stok_folders() -> list[dict]:
    """List semua subfolder di /stok beserta jumlah file di dalamnya."""
    _ensure_stok_dir()
    folders = []
    for f in sorted(STOK_DIR.iterdir()):
        if f.is_dir():
            file_count = sum(1 for x in f.iterdir() if x.is_file())
            folders.append({
                "foldername": f.name,
                "file_count": file_count,
            })
    return folders


def count_folder_files(foldername: str) -> int:
    """Hitung jumlah file di subfolder."""
    path = STOK_DIR / foldername
    if not path.exists() or not path.is_dir():
        return 0
    return sum(1 for f in path.iterdir() if f.is_file())


def pop_folder_file(foldername: str) -> Optional[tuple[str, str]]:
    """
    Ambil 1 file dari subfolder (urut nama), return (filename, content).
    File dipindah ke subfolder 'used' setelah diambil.
    """
    path = STOK_DIR / foldername
    if not path.exists() or not path.is_dir():
        return None
    files = sorted(f for f in path.iterdir() if f.is_file())
    if not files:
        return None
    target = files[0]
    content = target.read_text(encoding="utf-8", errors="ignore").strip()
    used_dir = path / "used"
    used_dir.mkdir(exist_ok=True)
    target.rename(used_dir / target.name)
    return target.name, content


def get_stok_file_lines(filename: str) -> list[str]:
    """Baca isi file per baris (non-empty)."""
    path = STOK_DIR / filename
    if not path.exists() or not path.is_file():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]


def count_stok_file_lines(filename: str) -> int:
    return len(get_stok_file_lines(filename))


def pop_stok_file_line(filename: str) -> Optional[str]:
    """Ambil baris pertama dari file dan hapus dari file (consume)."""
    path = STOK_DIR / filename
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return None
    item = non_empty[0].strip()
    remaining = non_empty[1:]
    path.write_text("\n".join(remaining) + ("\n" if remaining else ""), encoding="utf-8")
    return item
