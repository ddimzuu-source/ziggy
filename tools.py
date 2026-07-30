# tools.py

import subprocess
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



ALLOWED_COMMANDS = {
    "journalctl": {"-xe", "-n", "-u", "--since", "--no-pager", "-p"},
    "systemctl": {"status", "is-active", "is-enabled", "list-units"},
    "pacman": {"-Q", "-Qi", "-Qs", "-Ss", "-Si", "-Qu"},
    "uname": {"-a", "-r", "-m"},
    "df": {"-h"},
    "free": {"-h"},
}


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
        "function": lambda _: check_updates(),  # <-- lihat catatan di bawah
        "description": (
            "Cek daftar package yang bisa di-update di sistem (pacman -Qu). "
            "Tidak butuh input, gunakan input kosong atau tanda '-'."
        ),
    },
}

