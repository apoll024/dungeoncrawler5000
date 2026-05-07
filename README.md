# dungeoncrawler5000

A personal D&D reference assistant — search and generate content grounded in your indexed sourcebook library.

## Features
- PDF ingestion pipeline (your personally owned books)
- Semantic search with exact passage retrieval + citations
- RAG-powered generation: NPCs, settings, rules lookups
- Flask API + Docker deployment on your LAN

## Quick start

### 1. Ingest a book
```bash
python ingest/extract.py --pdf pdfs/PHB.pdf --source PHB --output chunks/phb.jsonl
python ingest/embed.py --input chunks/phb.jsonl
```

### 2. Query from CLI
```bash
python search/query.py "grappling rules" --top 8
python generate/generate.py ask "How does grappling work?"
python generate/generate.py npc "A disgraced city guard turned bounty hunter"
python generate/generate.py setting "Coastal town plagued by a drowned god"
```

### 3. Run as API (Docker)
```bash
docker compose up -d
curl -X POST http://192.168.1.55:5001/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "What are the rules for grappling?"}'
```

## Environment variables
| Variable | Description |
|---|---|
| `COPILOT_OAUTH_TOKEN` | Copilot OAuth token (gpt-4o-mini) |
| `GITHUB_TOKEN` | GitHub PAT (fallback via GitHub Models) |
| `COPILOT_MODEL` | Model override (default: gpt-4o-mini) |

## Book IDs (--source)
Use short identifiers: `PHB`, `DMG`, `MM`, `TCE`, `XGE`, `VGM`, `MPMM`, etc.
