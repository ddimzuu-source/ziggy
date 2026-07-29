# tools.py

from pathlib import Path
from config import ALLOWED_ROOT

def read_file(filepath: str) -> str:
    try:
        root = Path(ALLOWED_ROOT).resolve()
        target = Path(filepath).expanduser().resolve()

        if not target.is_relative_to(root):
            return f"[DITOLAK] Path di luar area yang diizinkan: {target}"
        if not target.is_file():
            return f"[ERROR] Bukan file atau tidak ditemukan: {target}"

        max_size = 100_000
        if target.stat().st_size > max_size:
            return f"[ERROR] File terlalu besar (>{max_size} bytes)."

        return target.read_text(errors="replace")
    except Exception as e:
        return f"[ERROR] Gagal baca file: {e}"


TOOLS = {
    "read_file": {
        "function": read_file,
        "description": "Baca isi file LOKAL (bukan URL). Input: path file lokal.",
    }
}