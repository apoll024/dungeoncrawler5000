"""SQLite tracking for ingested D&D sourcebooks, chunk text, and source-derived training material."""
import re
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS training_material (
            id      TEXT PRIMARY KEY,
            source  TEXT NOT NULL,
            page    INTEGER,
            kind    TEXT NOT NULL,
            title   TEXT,
            content TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_training_source ON training_material(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_training_kind ON training_material(kind)")
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


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _training_kind(text: str) -> str:
    low = text.lower()
    if any(w in low for w in ("spell", "casting time", "range:", "components", "duration")):
        return "spell_or_magic"
    if any(w in low for w in ("challenge", "armor class", "hit points", "actions", "legendary")):
        return "creature_or_statblock"
    if any(w in low for w in ("rule", "check", "saving throw", "advantage", "disadvantage", "condition")):
        return "rule"
    if any(w in low for w in ("city", "kingdom", "region", "deity", "faction", "history", "lore")):
        return "lore"
    if any(w in low for w in ("dungeon", "room", "corridor", "trap", "encounter")):
        return "encounter_design"
    return "reference"


def _training_title(text: str) -> str:
    lines = [l.strip(" #\t") for l in (text or "").splitlines() if l.strip()]
    for line in lines[:4]:
        if 3 <= len(line) <= 90 and not line.endswith("."):
            return line
    return _clean_text(text)[:80]


def build_training_items(chunks: list[dict]) -> list[dict]:
    """Create source-derived learning records from raw sourcebook chunks.

    These are not external facts. They are compact, searchable training notes
    derived deterministically from uploaded sourcebook text.
    """
    items = []
    for c in chunks or []:
        text = _clean_text(c.get("text", ""))
        if len(text) < 80:
            continue
        source = c["source"]
        page = c.get("page", 0)
        title = _training_title(c.get("text", ""))
        kind = _training_kind(text)
        items.append({
            "id": f"tm_{c['id']}",
            "source": source,
            "page": page,
            "kind": kind,
            "title": title,
            "content": text[:1800],
        })
    return items


def store_training_from_chunks(chunks: list[dict]) -> int:
    """Populate source-derived training material from chunk text."""
    items = build_training_items(chunks)
    if not items:
        return 0
    with _conn() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO training_material (id, source, page, kind, title, content) "
            "VALUES (?,?,?,?,?,?)",
            [(i["id"], i["source"], i["page"], i["kind"], i["title"], i["content"]) for i in items],
        )
    return len(items)


def rebuild_training_material() -> int:
    """Rebuild source-derived training material from all stored chunks."""
    with _conn() as conn:
        chunks = [dict(r) for r in conn.execute("SELECT id, source, page, text FROM chunks").fetchall()]
        conn.execute("DELETE FROM training_material")
    return store_training_from_chunks(chunks)


def training_count() -> int:
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM training_material").fetchone()[0]


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


def search_training(query: str, source: str = None, limit: int = 10) -> list[dict]:
    """Search the source-derived training material with simple term scoring."""
    terms = [t.lower().strip() for t in re.split(r"\W+", query or "") if len(t.strip()) > 2]
    if not terms:
        return []
    source_clause = "AND source = ?" if source else ""
    score_params = []
    score_parts = []
    for term in terms[:10]:
        like = f"%{term}%"
        score_parts.append("CASE WHEN lower(title || ' ' || content || ' ' || kind) LIKE ? THEN 1 ELSE 0 END")
        score_params.append(like)
    params = score_params + score_params
    if source:
        params.append(source)
    params.append(limit)
    score_sql = " + ".join(score_parts)
    with _conn() as conn:
        rows = conn.execute(
            f"""
            SELECT id, source, page, kind, title, content, ({score_sql}) AS score
            FROM training_material
            WHERE ({score_sql}) > 0 {source_clause}
            ORDER BY score DESC, source, page
            LIMIT ?
            """,
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
        conn.execute("DELETE FROM training_material WHERE source = ?", (source,))


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
