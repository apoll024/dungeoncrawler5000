# dungeoncrawler5000

A personal D&D reference assistant — search and generate content grounded in your indexed sourcebook library.

## Features
- PDF ingestion pipeline (your personally owned books)
- Semantic search with exact passage retrieval + citations
- RAG-powered generation: NPCs, monsters, settings, maps, rules lookups
- Streaming chat assistant grounded in uploaded sourcebooks
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
curl -X POST http://localhost:5001/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "What are the rules for grappling?"}'
```

## Environment variables
| Variable | Description | Default |
|---|---|---|
| `GITHUB_TOKEN` | GitHub OAuth/PAT token for GitHub Models API (preferred) | — |
| `GEMINI_API_KEY` | Google Gemini API key (fallback if no GITHUB_TOKEN) | — |
| `LLM_API_URL` | OpenAI-compatible LLM endpoint | `https://models.inference.ai.azure.com/chat/completions` |
| `LLM_MODEL` | Model name | `gpt-4o` |
| `LLM_TIMEOUT` | Request timeout in seconds | `60` |

> **Note:** The VM deployment uses a `docker-compose.override.yml` that sets the LLM provider and token. The override file is not committed to the repo as it contains credentials.

## Book IDs (--source)
Use short identifiers: `PHB`, `DMG`, `MM`, `TCE`, `XGE`, `VGM`, `MPMM`, etc.
