# test_react_format.py
# Tujuan: cek apakah qwen2.5-coder bisa ngikutin format ReAct sebelum kita
# kasih dia tools beneran

import requests

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen2.5-coder:1.5b"

SYSTEM_PROMPT = """Kamu adalah Ziggy, AI agent asisten Linux.
Kamu HARUS menjawab dengan format berikut, tidak boleh ada teks lain:

Thought: <penalaranmu singkat>
Final Answer: <jawaban akhir>

Contoh:
Thought: User nanya soal cuaca, saya tidak punya tool untuk itu, saya jawab langsung.
Final Answer: Maaf, saya belum bisa cek cuaca.
"""

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
    result = ask("Kenapa Hyprland saya sering crash setelah update?")
    print(result)
