# agent.py

import re
import requests
from config import OLLAMA_HOST, MODEL_NAME, MAX_ITERATIONS
from tools import TOOLS

SYSTEM_PROMPT = """Kamu adalah Ziggy, AI agent asisten Linux di sistem CachyOS/Hyprland.

Tools yang tersedia:
{tools_desc}

Gunakan format PERSIS seperti ini, tanpa teks tambahan apapun.

Jika butuh tool:
Thought: <alasanmu>
Action: <nama_tool>
Action Input: <argumen tool>

Jika sudah cukup info untuk menjawab (tidak perlu tool):
Thought: <alasanmu>
Final Answer: <jawaban>

ATURAN WAJIB:
- Kata kunci HARUS PERSIS "Final Answer:" (bukan "Jawaban:", bukan "Answer:", bukan terjemahan lain)
- Kata kunci HARUS PERSIS "Action:" dan "Action Input:"
- Jangan pernah menulis "Observation:" sendiri, itu akan diisi sistem
- Setelah Action Input, JANGAN menulis apapun lagi, tunggu observation
- HANYA gunakan tool yang ADA di daftar tools di atas. JANGAN PERNAH mencoba tool lain
  (seperti systemctl, apt, dpkg, pip, dll) meskipun tool itu ada di sistem Linux asli.
- Jika permintaan user butuh kemampuan yang TIDAK ADA di daftar tools (misal: restart
  service, install package, jalankan command), JANGAN mencoba tool apapun.
  Langsung jawab dengan jujur menggunakan Final Answer bahwa kamu belum punya
  kemampuan itu di fase sekarang.

Contoh 1 (butuh tool):
User: Kenapa config hyprland saya error?
Thought: Saya perlu membaca isi file config untuk tahu isinya.
Action: read_file
Action Input: /home/drmwnmass/.config/hypr/hyprland.conf

Contoh 2 (tidak butuh tool, pertanyaan umum):
User: Apa itu Wayland?
Thought: Ini pertanyaan pengetahuan umum, saya tidak perlu membaca file apapun.
Final Answer: Wayland adalah protokol display server pengganti X11 di Linux.

Contoh 3 (setelah observation, kasih jawaban lengkap):
Observation: kb_layout = us, bind = SUPER Q exec kitty
Thought: Saya sudah dapat isi filenya, sekarang saya bisa jawab lengkap.
Final Answer: Berdasarkan config, keybinding yang ada: SUPER+Q membuka terminal kitty.

Contoh 4 (butuh kemampuan yang belum ada):
User: Restart Waybar saya sekarang
Thought: Saya tidak punya tool untuk menjalankan command sistem seperti restart service.
Final Answer: Maaf, saya belum punya kemampuan untuk menjalankan command sistem 
(seperti restart service) di fase pengembangan sekarang. Saat ini saya hanya bisa 
membaca isi file.


Jangan menulis Action dan Final Answer sekaligus."""


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
                "stop": ["\nObservation", "Observation:"]
            },
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def parse_step(text):
    # Normalisasi variasi kata kunci yang sering "ketuker" oleh model kecil
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
    system = SYSTEM_PROMPT.format(tools_desc=build_tools_desc())
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_query},
    ]

    for step in range(MAX_ITERATIONS):
        print(f"\n--- Iterasi {step + 1} ---")
        output = call_ollama(messages)
        print(output)

        parsed = parse_step(output)
        messages.append({"role": "assistant", "content": output})

        if parsed["type"] == "final":
            print(f"\n Final Answer: {parsed['content']}")
            return parsed["content"]

        elif parsed["type"] == "action":
            tool_name = parsed["tool"]
            tool_input = parsed["input"]

            if tool_name not in TOOLS:
                observation = f"[ERROR] Tool '{tool_name}' tidak dikenal."
            else:
                observation = TOOLS[tool_name]["function"](tool_input)

            print(f"Observation: {observation[:300]}...")  # dipotong biar ga banjir terminal
            messages.append({"role": "user", "content": f"Observation: {observation}"})

        else:
            messages.append({
                "role": "user",
                "content": "Format kamu salah. Ikuti format Thought/Action/Action Input atau Thought/Final Answer."
            })

    print("⚠️ Max iterations tercapai tanpa Final Answer.")
    return None


if __name__ == "__main__":
    query = input("Tanya Ziggy: ")
    run_agent(query)