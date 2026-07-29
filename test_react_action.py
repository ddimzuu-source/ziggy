# test_react_action.py
# Tujuan: cek apakah model bisa milih Action + Action Input dengan format benar
# (tool-nya belum beneran jalan, cuma dicek formatnya dulu)

import requests

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen2.5-coder:1.5b"

SYSTEM_PROMPT = """Kamu adalah Ziggy, AI agent asisten Linux.
Kamu punya satu tool:

- read_file: baca isi sebuah file LOKAL di sistem. Input: path file lokal (bukan URL).

Gunakan format PERSIS seperti ini, tanpa teks tambahan apapun.

Jika butuh membaca file LOKAL untuk menjawab:
Thought: <alasanmu>
Action: read_file
Action Input: <path file lokal>

Jika sudah cukup info untuk menjawab TANPA perlu baca file (pengetahuan umum, definisi, konsep):
Thought: <alasanmu>
Final Answer: <jawaban>

Contoh 1 (butuh tool):
User: Kenapa config hyprland saya error?
Thought: Saya perlu membaca isi file config untuk tahu isinya.
Action: read_file
Action Input: /home/drmwnmass/.config/hypr/hyprland.conf

Contoh 2 (tidak butuh tool, pertanyaan umum):
User: Apa itu Wayland?
Thought: Ini pertanyaan pengetahuan umum, saya tidak perlu membaca file apapun.
Final Answer: Wayland adalah protokol display server pengganti X11 di Linux.

Jangan menulis Action dan Final Answer sekaligus.
Jangan gunakan Action jika pertanyaan bersifat umum/konseptual dan tidak menyebut file spesifik."""

def ask(query: str):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "stream": False,
    }
    response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["message"]["content"]


if __name__ == "__main__":
    # Kasus 1: harusnya milih Action (butuh baca file)
    print("=== TEST 1: butuh baca file ===")
    print(ask("Cek isi file /home/drmwnmass/.config/hypr/hyprland.conf, ada masalah apa?"))

    print("\n=== TEST 2: gak butuh tool ===")
    print(ask("Apa itu Hyprland secara umum?"))
