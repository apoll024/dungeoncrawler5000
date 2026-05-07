"""
Semantic search over indexed D&D sourcebooks.
Usage: python search/query.py "grappling rules" --top 8 [--source PHB]
"""
import argparse
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma"
COLLECTION = "dnd_index"
MODEL_NAME = "all-MiniLM-L6-v2"


def search(query: str, top_k: int = 8, source: str = None) -> list[dict]:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    col = client.get_or_create_collection(COLLECTION)
    model = SentenceTransformer(MODEL_NAME)

    embedding = model.encode([query]).tolist()
    where = {"source": source} if source else None

    results = col.query(
        query_embeddings=embedding,
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"]
    )

    return [
        {
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "score": round(1 - dist, 4),
        }
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--source", default=None)
    args = parser.parse_args()

    results = search(args.query, args.top, args.source)
    for r in results:
        print(f"\n[{r['source']} p.{r['page']} score={r['score']}]")
        print(r["text"])


if __name__ == "__main__":
    main()
