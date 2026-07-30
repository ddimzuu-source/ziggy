# agent.py

import re
import requests
from config import OLLAMA_HOST, MODEL_NAME, MAX_ITERATIONS
from tools import TOOLS

SYSTEM_PROMPT = """Kamu adalah Ziggy, AI agent asisten Linux di sistem CachyOS/Hyprland.

Tools yang tersedia:
{tools_desc}

Gunakan format PERSIS seperti ini, tanpa teks tambahan apapun:

Thought: <alasanmu>
Action: <nama_tool>
Action Input: <argumen tool>

ATAU jika tidak butuh tool:

Thought: <alasanmu>
Final Answer: <jawaban>

ATURAN WAJIB:
- Kata kunci HARUS PERSIS "Final Answer:", "Action:", "Action Input:"
- Jangan menulis "Observation:" sendiri, itu akan diisi sistem
- Setelah Action Input, JANGAN menulis apapun lagi
- HANYA gunakan tool yang ADA di daftar tools di atas
- run_command HANYA untuk command read-only. JANGAN mencoba command yang mengubah
  state sistem (restart, install, remove, dll) meskipun diminta - langsung jawab
  jujur belum bisa via Final Answer
- JANGAN PERNAH menulis "Contoh" atau melanjutkan pola contoh di bawah ini.
  Contoh HANYA referensi format, bukan template untuk dilanjutkan.
- JAWAB HANYA untuk pertanyaan user yang sekarang, jangan buat pertanyaan/skenario baru.

Referensi format (jangan ditiru isinya, hanya polanya):

[1] Butuh baca file:
Thought: Perlu membaca isi file config.
Action: read_file
Action Input: /home/drmwnmass/.config/hypr/hyprland.conf

[2] Butuh cek command sistem read-only:
Thought: Perlu cek status/log lewat command read-only.
Action: run_command
Action Input: systemctl status NetworkManager

[3] Tidak butuh tool / kemampuan belum ada:
Thought: Ini pertanyaan umum atau butuh kemampuan yang belum tersedia.
Final Answer: <jawaban langsung atau pengakuan keterbatasan>

[4] Cek update package sistem:
Thought: User tanya soal update, saya bisa cek pakai check_updates.
Action: check_updates
Action Input: -

SEKALI LAGI: jawab hanya untuk pertanyaan user berikut ini, jangan menulis contoh tambahan."""


# --- SAFETY NET LEVEL KODE (bukan bergantung ke model) ---
DESTRUCTIVE_INTENT_KEYWORDS = [
    "restart", "install", "uninstall", "hapus", "remove", "matikan",
    "stop", "reboot", "shutdown", "kill", "reinstall", "update sistem",
    "upgrade", "downgrade",
]

def check_destructive_intent(query: str) -> str | None:
    query_lower = query.lower()
    for kw in DESTRUCTIVE_INTENT_KEYWORDS:
        if kw in query_lower:
            return (
                f"Maaf, permintaan ini mengandung kata '{kw}' yang mengindikasikan "
                f"perubahan state sistem (restart/install/remove/dll). Ziggy di fase "
                f"sekarang hanya bisa membaca file dan menjalankan command read-only "
                f"(cek status, log, package) — belum bisa eksekusi perubahan apapun."
            )
    return None


def build_tools_desc():
    return "\n".join(f"- {name}: {meta['description']}" for name, meta in TOOLS.items())


def call_ollama(messages):
    resp = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {
                "stop": ["\nObservation", "Observation:"],
                "temperature": 0, 
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]

def parse_step(text):
    normalized = re.sub(r"^(Jawaban|Answer)\s*:", "Final Answer:", text, flags=re.MULTILINE)

    action_pos = normalized.find("Action:")
    final_pos = normalized.find("Final Answer:")

    if final_pos != -1 and (action_pos == -1 or final_pos < action_pos):
        content = normalized[final_pos + len("Final Answer:"):].strip()
        return {"type": "final", "content": content}

    if action_pos != -1:
        action_match = re.search(r"Action:\s*(\w+)", normalized)
        input_match = re.search(r"Action Input:\s*(.+)", normalized)
        if action_match and input_match:
            return {
                "type": "action",
                "tool": action_match.group(1).strip(),
                "input": input_match.group(1).strip().splitlines()[0],
            }

    return {"type": "unknown", "content": text}


def run_agent(user_query: str):
    early_refusal = check_destructive_intent(user_query)
    if early_refusal:
        print(f"\n⚠️  Ditolak di level kode (bukan model): {early_refusal}")
        return early_refusal

    system = SYSTEM_PROMPT.format(tools_desc=build_tools_desc())
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_query},
    ]

    unknown_count = 0
    seen_actions = {}

    for step in range(MAX_ITERATIONS):
        print(f"\n--- Iterasi {step + 1} ---")
        output = call_ollama(messages)

        parsed = parse_step(output)
        messages.append({"role": "assistant", "content": output})

        if parsed["type"] == "final":
            print(f"✅ Final Answer: {parsed['content']}")
            return parsed["content"]

        elif parsed["type"] == "action":
            tool_name = parsed["tool"]
            tool_input = parsed["input"]
            signature = (tool_name, tool_input)

            print(f"Thought/Action: {output.strip()}")

            if signature in seen_actions:
                print(f"⚠️  Action '{tool_name}' dengan input yang sama sudah pernah "
                      f"dipanggil sebelumnya. Menghentikan loop untuk mencegah pengulangan.")
                previous_observation = seen_actions[signature]
                return (f"Berdasarkan hasil pengecekan sebelumnya:\n{previous_observation}\n\n"
                        f"(Catatan: agent berhenti karena mencoba mengulang aksi yang sama.)")

            if tool_name not in TOOLS:
                observation = f"[ERROR] Tool '{tool_name}' tidak dikenal."
            else:
                observation = TOOLS[tool_name]["function"](tool_input)

            seen_actions[signature] = observation

            print(f"Observation: {observation[:300]}...")
            messages.append({"role": "user", "content": f"Observation: {observation}"})
            unknown_count = 0

        else:
            unknown_count += 1
            print(f"[UNKNOWN FORMAT] Raw output: {repr(output)}")

            if unknown_count >= 2:
                print("⚠️  Model nyangkut format 2x berturut-turut, pakai raw output sebagai jawaban.")
                return output.strip()

            messages.append({
                "role": "user",
                "content": "Format kamu salah. Ikuti format Thought/Action/Action Input atau Thought/Final Answer."
            })

    print("⚠️ Max iterations tercapai tanpa Final Answer.")
    return None


if __name__ == "__main__":
    query = input("Tanya Ziggy: ")
    run_agent(query)