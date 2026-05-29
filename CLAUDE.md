# DungeonCrawler5000

Personal D&D reference assistant — RAG pipeline over your own sourcebook PDFs with a Flask web UI.

## Architecture

```
pdfs/           → raw PDFs (git-ignored, user-supplied)
ingest/
  extract.py    → PyMuPDF PDF→pages→chunks
  embed.py      → sentence-transformers → ChromaDB vector store
  db.py         → SQLite: books, chunks, training_material tables
generate/
  generate.py   → LLM call wrappers (NPC, monster, setting, map, ask_stream)
search/
  query.py      → semantic search against ChromaDB
api/
  app.py        → Flask API + SSE streaming chat
  templates/    → single-page UI (index.html)
data/           → SQLite DB + ChromaDB (git-ignored, runtime)
chunks/         → intermediate JSONL (git-ignored)
```

## Key data stores

| Store | Path | What lives there |
|---|---|---|
| ChromaDB | `data/chroma/` | Vector embeddings for semantic search |
| SQLite | `data/books.db` | books, chunks (full text), training_material |

Both stores are git-ignored. The `sync_from_chroma()` call reconciles them on startup.

## LLM configuration

Uses an OpenAI-compatible API endpoint. Configure via env vars:

| Var | Default in generate.py | Override |
|---|---|---|
| `LLM_API_URL` | Gemini endpoint | Set to GitHub Models or any OpenAI-compat URL |
| `LLM_MODEL` | `gemini-3.5-flash` | `gpt-4o` for GitHub Models |
| `GITHUB_TOKEN` | — | Preferred auth method (GitHub Models) |
| `GEMINI_API_KEY` | — | Fallback auth |
| `LLM_TIMEOUT` | `60` | Seconds |

> Note: `generate.py` still defaults to Gemini in code. The deployed instance overrides via `docker-compose.override.yml` (not committed — contains credentials).

## Running locally

```bash
pip install -r requirements.txt

# Ingest a book
python ingest/extract.py --pdf pdfs/PHB.pdf --source PHB --output chunks/phb.jsonl
python ingest/embed.py --input chunks/phb.jsonl

# CLI queries
python search/query.py "grappling rules" --top 8
python generate/generate.py ask "How does grappling work?"

# Start API server
python api/app.py  # http://localhost:5001
```

## Docker

```bash
docker compose up -d          # port 5001
# Credentials go in docker-compose.override.yml (not committed)
```

## API surface

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Web UI |
| GET | `/health` | Liveness probe |
| GET | `/api/status` | Book count, chunk counts, LLM status |
| GET | `/api/books` | List ingested books |
| DELETE | `/api/books/<source>` | Remove a book and its chunks |
| POST | `/api/upload` | Upload + ingest a PDF |
| POST | `/api/chat` | SSE streaming chat |
| GET | `/api/search` | Search (mode: semantic/keyword/training) |
| GET | `/api/chunks/<source>` | Browse stored chunks |
| POST | `/api/training/rebuild` | Rebuild training_material from chunks |
| POST | `/api/generate/npc` | Generate NPC JSON |
| POST | `/api/generate/monster` | Generate monster stat block JSON |
| POST | `/api/generate/setting` | Generate setting JSON |
| POST | `/api/generate/map` | Generate dungeon map JSON |

Legacy routes: `/search`, `/ask`, `/ingest` (kept for backwards compat).

## Content generation schemas

All generators return JSON. Malformed LLM output is cleaned in `app.py` (`_parse_generated_json`) with fallback defaults (`_npc_defaults`, `_monster_defaults`, `_setting_defaults`, `_fallback_map`).

## Book IDs

Short uppercase identifiers: `PHB`, `DMG`, `MM`, `TCE`, `XGE`, `VGM`, `MPMM`, etc.

## Testing

No test suite currently. Manual testing via the web UI at `http://localhost:5001`.
