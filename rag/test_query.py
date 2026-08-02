# rag/test_query.py
import chromadb
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
CHROMA_DB_DIR = SCRIPT_DIR / "chroma_db"
COLLECTION_NAME = "ziggy_war_stories"

client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
collection = client.get_collection(COLLECTION_NAME)

queries = [
    "sistem gak bisa boot masuk emergency mode",
    "kenapa hyprland gak muncul setelah update",
    "resep membuat rendang",  # ini sengaja gak relevan, buat lihat behavior-nya
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