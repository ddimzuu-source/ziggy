# test_suite.py
# Jalankan dengan model yang aktif di config.py, ganti MODEL_NAME lalu run ulang

from agent import run_agent
import time

TEST_QUERIES = [
    "ada perubahan apa di config gua dibanding snapshot terakhir?",
    "snapshot apa aja yg pernah gua buat?",
    "restart waybar dong",  # harus ditolak di level kode, bukan model
    "apakah networkmanager saya jalan?",
    "ada error log ga hari ini?",
    "ada update gak buat sistem saya?",
]

if __name__ == "__main__":
    for i, q in enumerate(TEST_QUERIES, 1):
        print(f"\n{'='*60}\nTEST {i}: {q}\n{'='*60}")
        start = time.time()
        result = run_agent(q)
        elapsed = time.time() - start
        print(f"\n[Waktu: {elapsed:.1f}s] Hasil: {result}")