"""
Embed chunks and store in ChromaDB.
Usage: python ingest/embed.py --input chunks/phb.jsonl
"""
import argparse, json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma"
COLLECTION = "dnd_index"
MODEL_NAME = "all-MiniLM-L6-v2"
BATCH = 64


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def embed_chunks(chunks: list[dict]):
    model = SentenceTransformer(MODEL_NAME)
    col   = get_collection()

    texts = [c["text"] for c in chunks]
    ids   = [c["id"]   for c in chunks]
    metas = [{"source": c["source"], "page": c["page"]} for c in chunks]

    for i in range(0, len(chunks), BATCH):
        bt, bi, bm = texts[i:i+BATCH], ids[i:i+BATCH], metas[i:i+BATCH]
        embeddings = model.encode(bt, show_progress_bar=False).tolist()
        col.upsert(ids=bi, embeddings=embeddings, documents=bt, metadatas=bm)
        print(f"  batch {i//BATCH + 1}: {len(bt)} chunks upserted")

    # Write source text and derived training records immediately — AI learns only from uploaded books
    try:
        from ingest.db import store_chunks, store_training_from_chunks
        store_chunks(chunks)
        training_count = store_training_from_chunks(chunks)
        print(f"[embed] {len(chunks)} chunks written to SQLite")
        print(f"[embed] {training_count} source-derived training records written to SQLite")
    except Exception as e:
        print(f"[embed] SQLite write warning: {e}")

    print(f"[embed] ChromaDB total: {col.count()} chunks")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help=".jsonl from extract.py")
    args = parser.parse_args()

    chunks = [json.loads(l) for l in open(args.input, encoding="utf-8")]
    print(f"[embed] embedding {len(chunks)} chunks...")
    embed_chunks(chunks)


if __name__ == "__main__":
    main()
