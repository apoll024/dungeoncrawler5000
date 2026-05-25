"""SQLite tracking for ingested D&D sourcebooks + full chunk text store."""
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
    # Full chunk text — written on every ingest so the AI always has a source
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id     TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            page   INTEGER,
            text   TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")
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


def store_chunks(chunks: list[dict]):
    """Write chunk text to SQLite — called immediately after ingest so the AI can reference it."""
    if not chunks:
        return
    with _conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO chunks (id, source, page, text) VALUES (?,?,?,?)",
            [(c["id"], c["source"], c.get("page", 0), c["text"]) for c in chunks],
        )


def search_chunks(query: str, source: str = None, limit: int = 10) -> list[dict]:
    """Fast keyword search over chunk text — no ML model required."""
    terms = [t.strip() for t in query.split() if len(t.strip()) > 2]
    if not terms:
        return []
    clauses = " AND ".join(["text LIKE ?" for _ in terms])
    params  = [f"%{t}%" for t in terms]
    if source:
        clauses += " AND source = ?"
        params.append(source)
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(
            f"SELECT id, source, page, text FROM chunks WHERE {clauses} LIMIT ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_chunks(source: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Return all chunks for a source (paginated)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, source, page, substr(text,1,400) as text "
            "FROM chunks WHERE source = ? ORDER BY page LIMIT ? OFFSET ?",
            (source, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_book(source: str):
    with _conn() as conn:
        conn.execute("DELETE FROM books WHERE source = ?", (source,))
        conn.execute("DELETE FROM chunks WHERE source = ?", (source,))


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
