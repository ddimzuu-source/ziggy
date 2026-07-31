# tools.py

import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import difflib
import shutil
import json
from datetime import datetime
from pathlib import Path
from config import ALLOWED_ROOT,  HYPR_CONFIG_DIR, SNAPSHOT_DIR


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



ALLOWED_COMMANDS = {
    "journalctl": {"-xe", "-n", "-u", "--since", "--no-pager", "-p"},
    "systemctl": {"status", "is-active", "is-enabled", "list-units"},
    "pacman": {"-Q", "-Qi", "-Qs", "-Ss", "-Si", "-Qu"},
    "uname": {"-a", "-r", "-m"},
    "df": {"-h"},
    "free": {"-h"},
}

ALLOWED_FETCH_DOMAINS = {
    "archlinux.org",
}

ARCH_NEWS_RSS = "https://archlinux.org/feeds/news/"


FORBIDDEN_KEYWORDS = {
    "stop", "start", "restart", "disable", "mask", "kill",
    "-S", "-R", "-U", "--noconfirm", "rm", "reboot", "shutdown",
    "poweroff", "halt", ">", ">>", "|", "&", ";", "&&", "`", "$(",
}


def run_command(command_str: str) -> str:
    """
    Jalankan command sistem HANYA jika ada di whitelist.
    Tidak pakai shell=True — command di-split jadi list argumen.
    """
    try:
        parts = command_str.strip().split()
        if not parts:
            return "[ERROR] Command kosong."

        cmd_name = parts[0]

        # Cek 1: command dasarnya harus ada di whitelist
        if cmd_name not in ALLOWED_COMMANDS:
            return f"[DITOLAK] Command '{cmd_name}' tidak ada di whitelist."

        # Cek 2: cegah karakter/kata berbahaya di seluruh command
        for part in parts:
            if part in FORBIDDEN_KEYWORDS:
                return f"[DITOLAK] Argumen '{part}' termasuk kata terlarang."

        # Cek 3: kalau ada whitelist subcommand spesifik, minimal 1 harus cocok
        allowed_subs = ALLOWED_COMMANDS[cmd_name]
        if allowed_subs is not None:
            if not any(sub in parts[1:] for sub in allowed_subs):
                return (f"[DITOLAK] '{cmd_name}' butuh subcommand dari daftar "
                        f"yang diizinkan: {allowed_subs}")

        # Eksekusi aman — list argumen, bukan string shell
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            timeout=15,
        )

        output = result.stdout.strip()
        if result.returncode != 0:
            output += f"\n[stderr] {result.stderr.strip()}"

        # Batasi panjang output biar gak banjir context window model
        max_len = 3000
        if len(output) > max_len:
            output = output[:max_len] + "\n...[dipotong, output terlalu panjang]"

        return output if output else "[INFO] Command berhasil, tidak ada output."

    except subprocess.TimeoutExpired:
        return "[ERROR] Command timeout (>15 detik)."
    except Exception as e:
        return f"[ERROR] Gagal jalankan command: {e}"


def check_updates() -> str:
    """
    Cek package yang bisa di-update pakai pacman -Qu.
    Read-only — tidak menjalankan update apapun, hanya melihat daftarnya.
    """
    try:
        result = subprocess.run(
            ["pacman", "-Qu"],
            capture_output=True,
            text=True,
            timeout=15,
        )

        output = result.stdout.strip()

        # pacman -Qu return code 1 kalau tidak ada update sama sekali (bukan error)
        if result.returncode == 1 and not output:
            return "[INFO] Tidak ada update yang tersedia. Sistem sudah paling baru."

        if result.returncode not in (0, 1):
            return f"[ERROR] pacman gagal dijalankan: {result.stderr.strip()}"

        if not output:
            return "[INFO] Tidak ada update yang tersedia."

        lines = output.splitlines()
        count = len(lines)

        # Batasi list yang ditampilkan biar gak banjir context window
        max_show = 30
        shown = lines[:max_show]
        summary = f"[INFO] Ada {count} package yang bisa di-update:\n" + "\n".join(shown)

        if count > max_show:
            summary += f"\n...dan {count - max_show} package lainnya (dipotong)."

        return summary

    except subprocess.TimeoutExpired:
        return "[ERROR] Command timeout (>15 detik)."
    except Exception as e:
        return f"[ERROR] Gagal cek update: {e}"
        

def snapshot_config(_input: str = "") -> str:
    """
    Simpan salinan folder ~/.config/hypr/ ke snapshots/ dengan timestamp.
    Read-only terhadap config asli — hanya copy, tidak pernah modify.
    """
    try:
        source = Path(HYPR_CONFIG_DIR).resolve()
        root = Path(ALLOWED_ROOT).resolve()

        # Validasi sama seperti read_file — pastikan source dalam area yang diizinkan
        if not source.is_relative_to(root):
            return f"[DITOLAK] Source di luar area yang diizinkan: {source}"

        if not source.is_dir():
            return f"[ERROR] Folder config tidak ditemukan: {source}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_root = Path(SNAPSHOT_DIR).resolve()
        snapshot_root.mkdir(parents=True, exist_ok=True)

        dest = snapshot_root / f"hypr_{timestamp}"

        shutil.copytree(source, dest)

        # Simpan juga metadata kecil biar gampang dibaca nanti
        meta = {
            "timestamp": timestamp,
            "source": str(source),
            "file_count": sum(1 for _ in dest.rglob("*") if _.is_file()),
        }
        (dest / "_snapshot_meta.json").write_text(json.dumps(meta, indent=2))

        return (f"[INFO] Snapshot berhasil dibuat: {dest.name}\n"
                f"Menyimpan {meta['file_count']} file dari {source}")

    except Exception as e:
        return f"[ERROR] Gagal membuat snapshot: {e}"


def list_snapshots(_input: str = "") -> str:
    """List semua snapshot yang pernah dibuat, urut dari terbaru."""
    try:
        snapshot_root = Path(SNAPSHOT_DIR).resolve()
        if not snapshot_root.exists():
            return "[INFO] Belum ada snapshot yang dibuat."

        snapshots = sorted(
            [d for d in snapshot_root.iterdir() if d.is_dir()],
            reverse=True
        )
        if not snapshots:
            return "[INFO] Belum ada snapshot yang dibuat."

        lines = [f"- {s.name}" for s in snapshots[:10]]
        return f"[INFO] {len(snapshots)} snapshot ditemukan:\n" + "\n".join(lines)

    except Exception as e:
        return f"[ERROR] Gagal list snapshot: {e}"

def diff_config_after_update(snapshot_name: str = "") -> str:
    """
    Bandingkan snapshot config (default: yang terbaru) dengan kondisi
    ~/.config/hypr/ sekarang. Read-only, tidak mengubah apapun.
    """
    try:
        snapshot_root = Path(SNAPSHOT_DIR).resolve()
        if not snapshot_root.exists():
            return "[ERROR] Belum ada snapshot sama sekali. Jalankan snapshot_config dulu."

        snapshots = sorted(
            [d for d in snapshot_root.iterdir() if d.is_dir()],
            reverse=True
        )
        if not snapshots:
            return "[ERROR] Belum ada snapshot sama sekali. Jalankan snapshot_config dulu."

        # Pilih snapshot: kalau input kosong/'-', pakai yang terbaru
        target_snapshot = None
        cleaned_input = snapshot_name.strip().strip("-").strip()
        if not cleaned_input:
            target_snapshot = snapshots[0]
        else:
            for s in snapshots:
                if cleaned_input in s.name:
                    target_snapshot = s
                    break
            if target_snapshot is None:
                return f"[ERROR] Snapshot '{cleaned_input}' tidak ditemukan."

        current = Path(HYPR_CONFIG_DIR).resolve()
        if not current.is_dir():
            return f"[ERROR] Folder config saat ini tidak ditemukan: {current}"

        # Kumpulkan semua file relatif dari kedua sisi (exclude metadata snapshot)
        snap_files = {
            f.relative_to(target_snapshot) for f in target_snapshot.rglob("*")
            if f.is_file() and f.name != "_snapshot_meta.json"
        }
        current_files = {
            f.relative_to(current) for f in current.rglob("*") if f.is_file()
        }

        added = current_files - snap_files
        removed = snap_files - current_files
        common = snap_files & current_files

        report = [f"[INFO] Membandingkan snapshot '{target_snapshot.name}' dengan config saat ini:\n"]

        if added:
            report.append(f"File BARU (tidak ada di snapshot): {', '.join(str(f) for f in added)}")
        if removed:
            report.append(f"File HILANG (ada di snapshot, sekarang tidak ada): {', '.join(str(f) for f in removed)}")

        changed_count = 0
        for rel_path in sorted(common):
            old_file = target_snapshot / rel_path
            new_file = current / rel_path

            old_lines = old_file.read_text(errors="replace").splitlines()
            new_lines = new_file.read_text(errors="replace").splitlines()

            if old_lines == new_lines:
                continue

            changed_count += 1
            diff = list(difflib.unified_diff(
                old_lines, new_lines,
                fromfile=f"snapshot/{rel_path}",
                tofile=f"current/{rel_path}",
                lineterm="", n=1,
            ))
            # Batasi tiap file diff biar gak kepanjangan
            diff_snippet = "\n".join(diff[:20])
            report.append(f"\n--- Perubahan di {rel_path} ---\n{diff_snippet}")

        if changed_count == 0 and not added and not removed:
            report.append("Tidak ada perubahan sama sekali dibanding snapshot.")

        result = "\n".join(report)

        # Batasi panjang total output
        max_len = 3000
        if len(result) > max_len:
            result = result[:max_len] + "\n...[dipotong, output terlalu panjang]"

        return result

    except Exception as e:
        return f"[ERROR] Gagal diff config: {e}"


def get_changelog(keyword: str = "") -> str:
    """
    Ambil berita/changelog terbaru dari Arch Linux News RSS feed.
    Bisa difilter dengan keyword (nama package/komponen).
    Hanya mengakses domain yang di-whitelist (archlinux.org).
    """
    try:
        from urllib.parse import urlparse

        parsed_url = urlparse(ARCH_NEWS_RSS)
        if parsed_url.hostname not in ALLOWED_FETCH_DOMAINS:
            return f"[DITOLAK] Domain '{parsed_url.hostname}' tidak ada di whitelist."

        req = urllib.request.Request(
            ARCH_NEWS_RSS,
            headers={"User-Agent": "Ziggy-Agent/0.1 (local AI assistant)"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_data = response.read()

        root = ET.fromstring(raw_data)
        items = root.findall(".//item")

        if not items:
            return "[INFO] Tidak ada berita ditemukan di feed."

        keyword_clean = keyword.strip().strip("-").strip().lower()

        results = []
        for item in items[:15]:  # cek 15 berita terbaru
            title = item.findtext("title", default="").strip()
            pub_date = item.findtext("pubDate", default="").strip()
            link = item.findtext("link", default="").strip()
            description = item.findtext("description", default="").strip()

            # Kalau ada keyword, filter judul/deskripsi yang match
            if keyword_clean and keyword_clean not in title.lower() and keyword_clean not in description.lower():
                continue

            # Potong deskripsi biar gak kepanjangan (biasanya ada HTML tags juga)
            desc_short = re.sub(r"<[^>]+>", "", description)[:200]

            results.append(f"- [{pub_date}] {title}\n  {desc_short}...\n  {link}")

            if len(results) >= 5:  # maksimal 5 hasil biar gak banjir
                break

        if not results:
            return f"[INFO] Tidak ada berita yang cocok dengan keyword '{keyword_clean}' di 15 berita terbaru."

        header = f"[INFO] Berita Arch Linux terkait '{keyword_clean}':" if keyword_clean else "[INFO] Berita Arch Linux terbaru:"
        return header + "\n\n" + "\n\n".join(results)

    except (urllib.error.URLError, TimeoutError) as e:
        return f"[ERROR] Gagal mengakses internet (mungkin koneksi lambat/putus): {e}"
    except ET.ParseError as e:
        return f"[ERROR] Gagal parse RSS feed: {e}"
    except Exception as e:
        return f"[ERROR] Gagal ambil changelog: {e}"

TOOLS = {
    "read_file": {
        "function": read_file,
        "description": "Baca isi file LOKAL (bukan URL). Input: path file lokal.",
    },
    "run_command": {
        "function": run_command,
        "description": (
            "Jalankan command sistem READ-ONLY yang di-whitelist. "
            "Command yang diizinkan: journalctl (-xe/-n/-u/--since/-p), "
            "systemctl (status/is-active/is-enabled/list-units), "
            "pacman (-Q/-Qi/-Qs/-Ss/-Si/-Qu), uname, df -h, free -h. "
            "Input: command lengkap sebagai string, misal 'systemctl status waybar'."
        ),
            },
            "check_updates": {
                "function": lambda _: check_updates(),
                "description": "Cek daftar package yang bisa di-update (pacman -Qu). Input kosong atau '-'.",
            },
            "snapshot_config": {
                "function": snapshot_config,
                "description": (
                    "Buat snapshot (salinan) folder config Hyprland saat ini, diberi timestamp. "
                    "Berguna sebelum melakukan update sistem. Input kosong atau '-'."
                ),
            },

            "get_changelog": {
                    "function": get_changelog,
                    "description": (
                        "Cek BERITA/PERINGATAN breaking changes dari Arch Linux News (archlinux.org). "
                        "Gunakan untuk pertanyaan 'apa yang perlu diwaspadai', 'ada breaking changes', "
                        "'manual intervention' sebelum update. BUKAN untuk cek daftar package update. "
                        "Input: keyword (opsional) atau '-'."
                    ),
                },
            "list_snapshots": {
                "function": list_snapshots,
                "description": "Lihat daftar snapshot config yang pernah dibuat. Input kosong atau '-'.",
            },
            "diff_config_after_update": {
                    "function": diff_config_after_update,
                    "description": (
                        "Bandingkan config Hyprland saat ini dengan snapshot sebelumnya, tampilkan "
                        "apa yang berubah (file baru/hilang, dan diff isi file). "
                        "Input: nama snapshot spesifik (opsional), atau '-' untuk pakai snapshot terbaru."
                    ),
            },
            
        }

