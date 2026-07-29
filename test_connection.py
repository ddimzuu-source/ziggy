
import requests

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen2.5-coder:1.5b"

def test_ollama():
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "Halo, kamu siapa? Jawab singkat aja."}
        ],
        "stream": False,
    }

    response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=60)
    response.raise_for_status()

    data = response.json()
    print("=== RAW RESPONSE ===")
    print(data)
    print("\n=== ISI JAWABAN MODEL ===")
    print(data["message"]["content"])


if __name__ == "__main__":
    test_ollama()
