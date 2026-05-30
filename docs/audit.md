# DungeonCrawler5000 — Production Readiness Audit

## Critical — Fix Before Trusting In Prod

### 1. Flask dev server in production
`app.run()` is single-threaded and not production-grade. The Docker CMD `python api/app.py` means every deploy runs the dev server.

**Fix:**
```
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5001", "api.app:app"]
```

### 2. Path traversal in `/api/upload`
`source` comes from user form input, only `.upper()`-ed, then used as `pdf_dir / f"{source}.pdf"`. A source like `../../../etc/foo` (maxlength enforced client-side only) writes to an arbitrary path.

**File:** `api/app.py:229`

**Fix:**
```python
import re
source = re.sub(r'[^A-Z0-9]', '', source)[:12]
```

### 3. Missing `searchLore()` function — broken feature
The sidebar "Search Lore" button and Enter key handler both call `searchLore()` which is never defined in the JS. Clicking search throws `ReferenceError`. Feature is completely broken.

**File:** `api/templates/index.html:746-747`

### 4. No file size limit on uploads
No `MAX_CONTENT_LENGTH` set on Flask. A large PDF upload will run until OOM or the 5-minute thread timeout fires.

**File:** `api/app.py:216`

**Fix:**
```python
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB
```

### 5. Ingest blocks the request thread
`t.join(timeout=300)` blocks a Flask worker for up to 5 minutes during PDF ingest. With the dev server (single-threaded), this locks out every other request while a book is uploading.

**File:** `api/app.py:241`

---

## Medium — Worth Fixing

### 6. `embed_chunks` ignores the model singleton
`search/query.py` has a correct `_model` singleton, but `embed.py:21` always instantiates a fresh `SentenceTransformer(MODEL_NAME)` on every ingest. Model load takes 3-5s and loads ~90MB into RAM unnecessarily each time.

### 7. `api_status` creates two ChromaDB clients
Lines 153–154 open `PersistentClient` twice — a client is created, then immediately another is created to call `get_or_create_collection`. The first is thrown away.

**File:** `api/app.py:153-154`

### 8. Duplicate line in `ingest_route`
`source = data.get("source")` appears twice in a row. Harmless but indicates copy-paste.

**File:** `api/app.py:378-379`

### 9. No `.dockerignore`
`COPY . .` in the Dockerfile copies `.git/`, `pdfs/`, `chunks/`, and any `.env` into the image layer. Adds bloat and potential credential leakage.

### 10. Docker runs as root
No `USER` directive in the Dockerfile.

### 11. No CORS headers
Fine for the current Jinja2 UI (same-origin), but will block any separate frontend immediately.

---

## Minor / Acceptable for Home LAN

- No auth — intentional, LAN-only tool
- `chatHistory` grows unbounded in-browser (only last 10 sent to API — fine)
- Status polling every 30s even when idle — fine for one user
- `generate.py` LLM config read at import time — restart required to pick up new env vars, expected for Docker
- No request logging beyond Flask defaults

---

## Overall Verdict

**Not prod-ready** for public-facing use due to path traversal and missing WSGI server. For a single-user LAN deployment it mostly works, but:

- `searchLore()` is a user-visible broken feature
- Ingest blocks the entire server during upload
- Large PDF uploads are risky without a file size cap

**Priority fix order:** path traversal → gunicorn → `searchLore` → file size limit → `.dockerignore`

---

## React Frontend Uplift

### Effort estimate: 2–3 focused days

The API is already React-friendly — clean JSON responses, SSE streaming, REST endpoints. No backend changes needed beyond adding `flask-cors`.

### API mapping

| Current | React equivalent |
|---|---|
| Tab switching (JS) | Router or tab state with `useState` |
| `loadStatus()` + `setInterval` | `useEffect` + polling or SWR |
| `loadBooks()` → DOM innerHTML | `useQuery` or `useState` + `fetch` |
| `sendChat()` SSE streaming | Custom `useStream` hook wrapping `ReadableStream` |
| NPC/monster/setting render functions | Typed React components with props |
| Canvas map renderer (~150 lines) | `useRef` canvas component with `useEffect` |

### Tricky pieces

- **Canvas map renderer** — needs a `useEffect` that redraws when map data changes, with a `useRef` for the canvas element
- **SSE streaming state** — cursor + partial text is cleaner with `useReducer` but requires care to avoid stale closure bugs

### Recommended stack

- **Vite + React 18 + TypeScript** — fast build, the JSON schemas in `generate.py` are well-defined and straightforward to type
- **No state management library needed** — `useState`/`useContext` is enough at this scale
- **Serving:** build to static files and serve from Flask (`app.static_folder`), or drop an nginx container in front

### Only backend change needed

```bash
pip install flask-cors
```

```python
# api/app.py
from flask_cors import CORS
CORS(app)
```

### Proposed project structure

```
frontend/
  src/
    components/
      Sidebar.tsx         # book list + upload
      ChatPane.tsx        # SSE streaming chat
      NpcGenerator.tsx
      MonsterGenerator.tsx
      SettingGenerator.tsx
      MapGenerator.tsx    # canvas renderer
    hooks/
      useStream.ts        # SSE streaming hook
      useStatus.ts        # polling hook
    api/
      client.ts           # typed fetch wrappers
    types/
      index.ts            # NPC, Monster, Setting, Map JSON schemas as TS types
    App.tsx
  vite.config.ts
```
