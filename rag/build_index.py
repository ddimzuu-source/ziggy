# rag/build_index.py
# Baca semua war story JSON, index ke Chroma vector DB

import json
import sys
from pathlib import Path

import chromadb

# Path setup — biar bisa dijalankan dari mana aja
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
WAR_STORIES_DIR = PROJECT_ROOT / "war_stories"
CHROMA_DB_DIR = SCRIPT_DIR / "chroma_db"

COLLECTION_NAME = "ziggy_war_stories"


def load_war_stories():
    """Baca semua file .json di war_stories/"""
    stories = []
    if not WAR_STORIES_DIR.exists():
        print(f"[ERROR] Folder {WAR_STORIES_DIR} tidak ditemukan.")
        sys.exit(1)

    json_files = sorted(WAR_STORIES_DIR.glob("*.json"))
    if not json_files:
        print(f"[ERROR] Tidak ada file .json di {WAR_STORIES_DIR}.")
        sys.exit(1)

    for f in json_files:
        try:
            data = json.loads(f.read_text())
            stories.append(data)
        except json.JSONDecodeError as e:
            print(f"[WARNING] Gagal parse {f.name}: {e}")

    return stories


def story_to_document(story: dict) -> str:
    """
    Ubah war story JSON jadi 1 blok teks yang bagus untuk embedding.
    Digabung semua field penting jadi narasi yang koheren.
    """
    solusi_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(story.get("solusi", [])))
    diagnosis_text = "\n".join(f"  - {d}" for d in story.get("diagnosis_tools", []))
    komponen_text = ", ".join(story.get("komponen", []))

    doc = f"""JUDUL: {story.get('judul', '')}
KOMPONEN: {komponen_text}

GEJALA:
{story.get('gejala', '')}

PENYEBAB:
{story.get('penyebab', '')}

SOLUSI:
{solusi_text}

DIAGNOSIS TOOLS:
{diagnosis_text}

PENCEGAHAN:
{story.get('pencegahan', '')}"""

    return doc


def build_index():
    stories = load_war_stories()
    print(f"[INFO] Ditemukan {len(stories)} war story.")

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    # Hapus collection lama kalau ada, biar index selalu fresh dari war_stories/ saat ini
    try:
        client.delete_collection(COLLECTION_NAME)
        print("[INFO] Collection lama dihapus, membuat ulang.")
    except Exception:
        pass  # belum ada collection sebelumnya, gapapa

    collection = client.create_collection(name=COLLECTION_NAME)

    documents = []
    metadatas = []
    ids = []

    for story in stories:
        doc_text = story_to_document(story)
        documents.append(doc_text)
        metadatas.append({
            "judul": story.get("judul", ""),
            "komponen": ", ".join(story.get("komponen", [])),
            "tanggal": story.get("tanggal", ""),
        })
        ids.append(story.get("id", str(len(ids))))

    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"[INFO] Berhasil index {len(documents)} war story ke Chroma.")
    print(f"[INFO] Database tersimpan di: {CHROMA_DB_DIR}")


if __name__ == "__main__":
    build_index()