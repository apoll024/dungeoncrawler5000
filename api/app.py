"""Flask API + UI for DungeonCrawler5000."""
import json, os, sys, tempfile, threading
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

sys.path.insert(0, str(Path(__file__).parent.parent))
from search.query import search
from generate.generate import ask_stream, generate_npc, generate_monster, generate_setting, generate_map
from ingest.extract import extract_pages, chunk_pages
from ingest.embed import embed_chunks, CHROMA_PATH, COLLECTION
from ingest.db import (
    list_books, record_book, delete_book, sync_from_chroma, search_chunks, get_chunks,
    search_training, rebuild_training_material, training_count,
)

app = Flask(__name__)

_ingest_lock = threading.Lock()


def _parse_generated_json(raw: str):
    clean = (raw or "").strip()
    if clean.startswith("```"):
        parts = clean.split("```")
        clean = parts[1] if len(parts) > 1 else clean
        if clean.startswith("json"):
            clean = clean[4:]
        clean = clean.strip()
    try:
        return json.loads(clean)
    except Exception:
        start = clean.find("{")
        if start < 0:
            raise
        return json.JSONDecoder().raw_decode(clean[start:])[0]


def _npc_defaults(npc):
    if not isinstance(npc, dict):
        return npc
    npc.setdefault("name", "Source-Inspired NPC")
    npc.setdefault("ancestry", "")
    npc.setdefault("role", "")
    npc.setdefault("appearance", "")
    npc.setdefault("personality_traits", [])
    npc.setdefault("ideal", "")
    npc.setdefault("bond", "")
    npc.setdefault("flaw", "")
    npc.setdefault("backstory", "")
    npc.setdefault("plot_hooks", [])
    npc.setdefault("stat_block_suggestions", {"cr": "", "key_abilities": []})
    if not isinstance(npc["personality_traits"], list):
        npc["personality_traits"] = [str(npc["personality_traits"])]
    if not isinstance(npc["plot_hooks"], list):
        npc["plot_hooks"] = [str(npc["plot_hooks"])]
    if not isinstance(npc["stat_block_suggestions"], dict):
        npc["stat_block_suggestions"] = {"cr": "", "key_abilities": []}
    npc["stat_block_suggestions"].setdefault("key_abilities", [])
    return npc


def _monster_defaults(monster):
    if not isinstance(monster, dict):
        return monster
    monster.setdefault("name", "Source-Inspired Creature")
    monster.setdefault("size", "")
    monster.setdefault("type", "")
    monster.setdefault("alignment", "")
    monster.setdefault("challenge_rating", "?")
    monster.setdefault("xp", 0)
    monster.setdefault("hit_points", "?")
    monster.setdefault("armor_class", "?")
    monster.setdefault("speed", "?")
    monster.setdefault("ability_scores", {})
    monster.setdefault("senses", "")
    monster.setdefault("languages", "")
    monster.setdefault("special_abilities", [])
    monster.setdefault("actions", [])
    monster.setdefault("description", "")
    monster.setdefault("lore", "")
    for key in ("special_abilities", "actions", "legendary_actions", "saving_throws",
                "skills", "damage_resistances", "condition_immunities"):
        if key in monster and not isinstance(monster[key], list):
            monster[key] = [str(monster[key])]
    return monster


def _setting_defaults(setting):
    if not isinstance(setting, dict):
        return setting
    setting.setdefault("name", "Source-Inspired Setting")
    setting.setdefault("premise", "")
    setting.setdefault("region_type", "")
    for key in ("factions", "key_conflicts", "adventure_seeds", "rumors"):
        setting.setdefault(key, [])
        if not isinstance(setting[key], list):
            setting[key] = [str(setting[key])]
    return setting


def _fallback_map(description: str, raw: str):
    theme = (description or "").strip() or "source-inspired dungeon"
    name = "Source-Inspired " + theme[:52].strip().title()
    rooms = [
        (1, "Threshold Watch", "entrance", 4, 28, 7, 7, "A guarded entry point shaped by the requested sourcebook theme.", [2]),
        (2, "Crooked Passage", "corridor", 12, 31, 9, 2, "A narrow connector with cover, echoes, and room for an ambush.", [1, 3, 4]),
        (3, "Supply Den", "room", 23, 25, 8, 7, "A side chamber with signs of occupation and practical dungeon supplies.", [2]),
        (4, "Crossroads Grotto", "chamber", 24, 34, 10, 8, "The central chamber; use source-derived lore details from the generator notes.", [2, 5, 6, 7]),
        (5, "Hidden Cache", "treasure", 38, 26, 7, 7, "A concealed prize or clue that points deeper into the complex.", [4]),
        (6, "Snare Hall", "trap", 38, 38, 8, 5, "A hazardous approach that rewards careful exploration.", [4, 8]),
        (7, "Secret Cut", "secret", 25, 47, 6, 5, "A hidden route for scouts, prisoners, or monsters to bypass the main path.", [4, 9]),
        (8, "Boss Chamber", "boss", 50, 35, 10, 10, "The final confrontation area tied to the requested dungeon premise.", [6]),
        (9, "Lower Stair", "stairs", 34, 52, 6, 6, "A way down or out, useful for expanding the map into another level.", [7]),
    ]
    return {
        "name": name,
        "theme": f"{theme}. Fallback layout used after Gemini returned malformed map text.",
        "rooms": [
            {"id": rid, "name": rname, "type": rtype, "x": x, "y": y, "w": w, "h": h,
             "description": desc, "connections": links}
            for rid, rname, rtype, x, y, w, h, desc, links in rooms
        ],
        "source_notes": (raw or "")[:800],
    }


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return jsonify({"error": str(e), "detail": traceback.format_exc()[-500:]}), 500

@app.errorhandler(500)
def handle_500(e):
    return jsonify({"error": str(e)}), 500


@app.route("/favicon.ico")
def favicon():
    return "", 204

# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/status")
def api_status():
    try:
        import chromadb as _cdb
        client = _cdb.PersistentClient(path=str(CHROMA_PATH))
        col    = _cdb.PersistentClient(path=str(CHROMA_PATH)).get_or_create_collection(COLLECTION)
        vec_chunks = col.count()
    except Exception:
        vec_chunks = 0

    # Count text chunks stored directly in SQLite
    try:
        import sqlite3
        from ingest.db import DB_PATH
        conn = sqlite3.connect(str(DB_PATH))
        sql_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        conn.close()
    except Exception:
        sql_chunks = 0

    token   = os.getenv("GEMINI_API_KEY", "")
    llm_url = os.getenv("LLM_API_URL", "")
    llm_ok  = bool(token and llm_url)

    books = list_books()
    return jsonify({
        "llm":        "online" if llm_ok else "unconfigured",
        "books":      len(books),
        "chunks":     vec_chunks,
        "sql_chunks": sql_chunks,
        "training_items": training_count(),
    })


# ── UI ────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    sync_from_chroma()
    books = list_books()
    return render_template("index.html", books=books)


# ── Book library ──────────────────────────────────────────────────────────────

@app.route("/api/books")
def api_books():
    sync_from_chroma()
    return jsonify(list_books())


@app.route("/api/books/<source>", methods=["DELETE"])
def api_delete_book(source):
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col    = client.get_or_create_collection(COLLECTION)
        # Delete all chunks from this source
        results = col.get(where={"source": source}, include=[])
        if results["ids"]:
            col.delete(ids=results["ids"])
        delete_book(source)
        return jsonify({"status": "deleted", "source": source})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f      = request.files["file"]
    source = request.form.get("source", "").strip().upper()
    if not source:
        source = Path(f.filename).stem.upper()[:10]
    if not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Only PDF files accepted"}), 400

    pdf_dir = Path(__file__).parent.parent / "pdfs"
    pdf_dir.mkdir(exist_ok=True)
    pdf_path = pdf_dir / f"{source}.pdf"
    f.save(str(pdf_path))

    def do_ingest():
        with _ingest_lock:
            pages  = extract_pages(str(pdf_path))
            chunks = chunk_pages(pages, source)
            embed_chunks(chunks)
            record_book(source, f.filename, len(pages), len(chunks))

    t = threading.Thread(target=do_ingest, daemon=True)
    t.start()
    t.join(timeout=300)  # wait up to 5 min

    books = list_books()
    bk    = next((b for b in books if b["source"] == source), {})
    return jsonify({"status": "ingested", "source": source,
                    "pages": bk.get("pages", 0), "chunks": bk.get("chunks", 0)})


# ── Chat (SSE streaming) ──────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data     = request.json or {}
    question = data.get("question", "").strip()
    history  = data.get("history", [])
    if not question:
        return jsonify({"error": "question required"}), 400

    def generate():
        try:
            for token in ask_stream(question, history=history):
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Library reference endpoints ───────────────────────────────────────────────

@app.route("/api/search")
def api_search():
    """Search uploaded book content. mode=semantic (default) or keyword."""
    q      = request.args.get("q", "").strip()
    source = request.args.get("source") or None
    mode   = request.args.get("mode", "semantic")
    limit  = min(int(request.args.get("limit", 8)), 20)
    if not q:
        return jsonify([])
    if mode == "keyword":
        rows = search_chunks(q, source=source, limit=limit)
        return jsonify([{"source": r["source"], "page": r["page"],
                         "text": r["text"][:500], "score": None, "mode": "keyword"}
                        for r in rows])
    if mode == "training":
        rows = search_training(q, source=source, limit=limit)
        return jsonify([{"source": r["source"], "page": r["page"], "kind": r["kind"],
                         "title": r["title"], "text": r["content"][:500],
                         "score": r.get("score"), "mode": "training"}
                        for r in rows])
    results = search(q, top_k=limit, source=source)
    return jsonify([{"source": r["source"], "page": r["page"],
                     "text": r["text"][:500], "score": r.get("score"), "mode": "semantic"}
                    for r in results])


@app.route("/api/chunks/<source>")
def api_chunks_by_source(source):
    """Browse stored chunk text for a specific book."""
    limit  = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    return jsonify(get_chunks(source.upper(), limit=limit, offset=offset))


@app.route("/api/training/rebuild", methods=["POST"])
def api_training_rebuild():
    """Rebuild source-derived training material from stored sourcebook chunks."""
    return jsonify({"status": "ok", "training_items": rebuild_training_material()})


# ── Generators ────────────────────────────────────────────────────────────────

@app.route("/api/generate/npc", methods=["POST"])
def api_npc():
    data   = request.get_json(silent=True) or {}
    result = generate_npc(data.get("description", ""), data.get("top", 6))
    try:
        return jsonify({"npc": _npc_defaults(_parse_generated_json(result))})
    except Exception:
        return jsonify({"npc": result})


@app.route("/api/generate/monster", methods=["POST"])
def api_monster():
    data   = request.get_json(silent=True) or {}
    result = generate_monster(data.get("description", ""), data.get("top", 8))
    try:
        return jsonify({"monster": _monster_defaults(_parse_generated_json(result))})
    except Exception:
        return jsonify({"monster": result})


@app.route("/api/generate/setting", methods=["POST"])
def api_setting():
    data   = request.get_json(silent=True) or {}
    result = generate_setting(data.get("description", ""), data.get("top", 6))
    try:
        return jsonify({"setting": _setting_defaults(_parse_generated_json(result))})
    except Exception:
        return jsonify({"setting": result})


@app.route("/api/generate/map", methods=["POST"])
def api_map():
    data   = request.get_json(silent=True) or {}
    result = generate_map(data.get("description", ""), data.get("top", 4))
    try:
        return jsonify({"map": _parse_generated_json(result)})
    except Exception:
        return jsonify({"map": _fallback_map(data.get("description", ""), result)})


# ── Legacy JSON routes ────────────────────────────────────────────────────────

@app.route("/search", methods=["POST"])
def search_route():
    data    = request.get_json(silent=True) or {}
    results = search(data.get("query", ""), data.get("top", 8), data.get("source"))
    return jsonify({"results": results})


@app.route("/ask", methods=["POST"])
def ask_route():
    data = request.get_json(silent=True) or {}
    return jsonify({"answer": "".join(ask_stream(data.get("question", "")))})


@app.route("/ingest", methods=["POST"])
def ingest_route():
    data     = request.get_json(silent=True) or {}
    pdf_path = data.get("pdf_path")
    source   = data.get("source")
    source   = data.get("source")
    if not pdf_path or not source:
        return jsonify({"error": "pdf_path and source required"}), 400
    pages  = extract_pages(pdf_path)
    chunks = chunk_pages(pages, source)
    embed_chunks(chunks)
    record_book(source, Path(pdf_path).name, len(pages), len(chunks))
    return jsonify({"status": "ok", "pages": len(pages), "chunks": len(chunks)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
