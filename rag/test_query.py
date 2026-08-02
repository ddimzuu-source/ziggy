# rag/test_query.py
import chromadb
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CHROMA_DB_DIR = SCRIPT_DIR / "chroma_db"
COLLECTION_NAME = "ziggy_war_stories"

client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
collection = client.get_collection(COLLECTION_NAME)

queries = [
    "waybar muncul dua kali di layar",       # harus ketemu #003
    "hyprlock error pas mau lock screen",     # harus ketemu #004
    "abis update hyprland config error semua",  # harus ketemu #002
    "sistem masuk emergency mode gabisa boot",   # harus ketemu #001
    "hyprlock error pas mau lock screen",
    "kenapa sddm masih tema default",    
    "logo distro di terminal ku salah, kok jadi arch bukan cachyos",
    "prompt terminal ku background-nya putus putus gak nyambung",
    "install paket AUR error 404 gagal download",
    "pacman gagal update gara-gara mirror",
    ----
]

for q in queries:
    print(f"\n{'='*50}")
    print(f"QUERY: {q}")
    print('='*50)
    results = collection.query(query_texts=[q], n_results=2)

    for i, doc in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        metadata = results["metadatas"][0][i]
        print(f"\n[Hasil {i+1}] Jarak: {distance:.4f} | Judul: {metadata['judul']}")
        print(doc[:200] + "...")