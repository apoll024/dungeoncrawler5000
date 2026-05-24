"""SQLite tracking for ingested D&D sourcebooks."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "books.db"


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            source      TEXT PRIMARY KEY,
            filename    TEXT,
            pages       INTEGER,
            chunks      INTEGER,
            ingested_at TEXT
        )
    """)
    conn.commit()
    return conn


def record_book(source: str, filename: str, pages: int, chunks: int):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO books (source, filename, pages, chunks, ingested_at) VALUES (?,?,?,?,?)",
            (source, filename, pages, chunks, datetime.now(timezone.utc).isoformat()),
        )


def list_books() -> list[dict]:
    with _conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM books ORDER BY ingested_at").fetchall()]


def delete_book(source: str):
    with _conn() as conn:
        conn.execute("DELETE FROM books WHERE source = ?", (source,))


def sync_from_chroma():
    """Populate books DB from ChromaDB metadata (for PDFs ingested before DB existed)."""
    try:
        import chromadb
        from ingest.embed import CHROMA_PATH, COLLECTION
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col = client.get_or_create_collection(COLLECTION)
        existing = {b["source"] for b in list_books()}
        # Sample metadata to find unique sources
        results = col.get(limit=10000, include=["metadatas"])
        sources: dict[str, int] = {}
        for meta in results["metadatas"]:
            src = meta.get("source", "UNKNOWN")
            sources[src] = sources.get(src, 0) + 1
        for src, chunk_count in sources.items():
            if src not in existing:
                record_book(src, f"{src}.pdf", 0, chunk_count)
    except Exception:
        pass  # ChromaDB may be empty on first run
