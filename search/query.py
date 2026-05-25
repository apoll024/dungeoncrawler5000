"""
Semantic search over indexed D&D sourcebooks.
Usage: python search/query.py "grappling rules" --top 8 [--source PHB]
"""
import argparse, sys
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma"
COLLECTION  = "dnd_index"
MODEL_NAME  = "all-MiniLM-L6-v2"

# Singleton — loading SentenceTransformer takes 3-5s; only do it once per process
_model: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def search(query: str, top_k: int = 8, source: str = None) -> list[dict]:
    """Semantic search via ChromaDB. Falls back to SQLite keyword search if index is empty."""
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col    = client.get_or_create_collection(COLLECTION)
        count  = col.count()

        if count == 0:
            # ChromaDB empty — fall back to SQLite keyword search
            return _sqlite_fallback(query, top_k, source)

        model     = _get_model()
        embedding = model.encode([query]).tolist()
        where     = {"source": source} if source else None
        n         = min(top_k, count)

        results = col.query(
            query_embeddings=embedding,
            n_results=n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "text":   doc,
                "source": meta["source"],
                "page":   meta["page"],
                "score":  round(1 - dist, 4),
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]
    except Exception as e:
        print(f"[search] ChromaDB error ({e}), falling back to SQLite", file=sys.stderr)
        return _sqlite_fallback(query, top_k, source)


def _sqlite_fallback(query: str, top_k: int, source: str) -> list[dict]:
    """Keyword search directly against SQLite chunks table — no ML model needed."""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from ingest.db import search_chunks
        rows = search_chunks(query, source=source, limit=top_k)
        return [{"text": r["text"], "source": r["source"], "page": r["page"], "score": None}
                for r in rows]
    except Exception as e:
        print(f"[search] SQLite fallback error: {e}", file=sys.stderr)
        return []


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
