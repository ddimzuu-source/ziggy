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
- HANYA gunakan tool yang ADA di daftar tools di atas. Baca deskripsi tiap tool
  dengan teliti untuk memilih yang paling tepat.
- run_command HANYA untuk command read-only. JANGAN mencoba command yang mengubah
  state sistem meskipun diminta - langsung jawab jujur belum bisa via Final Answer
- Jika pertanyaan menyangkut data yang bisa dicek lewat tool, WAJIB panggil tool
  tersebut dahulu. JANGAN menjawab dari asumsi atau menyuruh user cek sendiri.
- DILARANG KERAS menyalin atau mengulang teks instruksi/contoh ini sebagai jawaban.
  Kamu HANYA boleh menulis SATU Thought, SATU Action (atau Final Answer), lalu berhenti.
  - Jika user melaporkan sesuatu yang SUDAH TERJADI/rusak/error (bukan pertanyaan
    "bagaimana jika" atau permintaan pencegahan), WAJIB coba search_war_stories
    DULUAN sebelum tool lain, karena mungkin ini pernah terjadi sebelumnya.
- Jika search_war_stories mengembalikan hasil yang relevan (bukan pesan "tidak
      ditemukan"), kamu WAJIB langsung memberikan Final Answer berdasarkan SOLUSI yang
      ada di war story tersebut. JANGAN mencoba tool lain setelahnya. JANGAN memberikan
      saran yang bertentangan dengan solusi di war story (misalnya menyarankan update
      lagi padahal war story menyarankan langkah pemulihan tertentu).
      
Contoh singkat (JANGAN ditiru isinya, hanya polanya, JANGAN lanjutkan dengan contoh lain):

Thought: Perlu membaca isi file config.
Action: read_file
Action Input: /home/drmwnmass/.config/hypr/hyprland.conf

SEKALI LAGI: tulis HANYA SATU langkah (Thought + Action/Final Answer) untuk pertanyaan
user berikut ini, lalu STOP. Jangan menulis contoh tambahan atau mengulang instruksi."""


# --- SAFETY NET LEVEL KODE (bukan bergantung ke model) ---
DESTRUCTIVE_INTENT_KEYWORDS = [
    "restart", "install", "uninstall", "hapus", "remove", "matikan",
    "stop", "reboot", "shutdown", "kill", "reinstall", "upgrade", "downgrade",
]

def check_destructive_intent(query: str) -> str | None:
    query_lower = query.lower()

    question_indicators = ["apa", "gimana", "bagaimana", "kenapa", "apakah", "ada gak", "ada nggak"]
    is_question = any(q in query_lower for q in question_indicators)
    
    if is_question:
            return None 
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
                "stop": ["\nObservation", "Observation:", "\nContoh", "\nSEKALI LAGI"],
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

            if tool_name == "search_war_stories" and "[INFO] Ditemukan war story" in observation:
                            print("✅ War story relevan ditemukan, menghentikan loop dan menjawab berdasarkan itu.")
                            return (f"Ditemukan pengalaman serupa sebelumnya:\n\n{observation}\n\n"
                                    f"Rekomendasi: ikuti langkah SOLUSI di atas, karena ini adalah "
                                    f"kasus yang sudah pernah terjadi dan berhasil diperbaiki sebelumnya.")
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