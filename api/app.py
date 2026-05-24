"""Flask API + UI for DungeonCrawler5000."""
import json, os, sys, tempfile, threading
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

sys.path.insert(0, str(Path(__file__).parent.parent))
from search.query import search
from generate.generate import ask_stream, generate_npc, generate_monster, generate_setting
from ingest.extract import extract_pages, chunk_pages
from ingest.embed import embed_chunks, CHROMA_PATH, COLLECTION
from ingest.db import list_books, record_book, delete_book, sync_from_chroma

app = Flask(__name__)

_ingest_lock = threading.Lock()


@app.errorhandler(Exception)
def handle_exception(e):
    import traceback
    return jsonify({"error": str(e), "detail": traceback.format_exc()[-500:]}), 500

@app.errorhandler(500)
def handle_500(e):
    return jsonify({"error": str(e)}), 500

# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/status")
def api_status():
    import chromadb, requests as _req
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        col    = client.get_or_create_collection(COLLECTION)
        chunks = col.count()
    except Exception:
        chunks = 0

    ollama_url = os.getenv("LLM_API_URL", "http://ollama:11434/v1/chat/completions")
    base_url   = ollama_url.replace("/v1/chat/completions", "")
    try:
        r      = _req.get(f"{base_url}/api/tags", timeout=3)
        ollama = "online" if r.ok else "offline"
    except Exception:
        ollama = "offline"

    books  = list_books()
    return jsonify({"ollama": ollama, "books": len(books), "chunks": chunks})


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


# ── Generators ────────────────────────────────────────────────────────────────

@app.route("/api/generate/npc", methods=["POST"])
def api_npc():
    data   = request.get_json(silent=True) or {}
    result = generate_npc(data.get("description", ""), data.get("top", 6))
    try:
        return jsonify({"npc": json.loads(result)})
    except Exception:
        return jsonify({"npc": result})


@app.route("/api/generate/monster", methods=["POST"])
def api_monster():
    data   = request.get_json(silent=True) or {}
    result = generate_monster(data.get("description", ""), data.get("top", 8))
    try:
        return jsonify({"monster": json.loads(result)})
    except Exception:
        return jsonify({"monster": result})


@app.route("/api/generate/setting", methods=["POST"])
def api_setting():
    data   = request.get_json(silent=True) or {}
    result = generate_setting(data.get("description", ""), data.get("top", 6))
    try:
        return jsonify({"setting": json.loads(result)})
    except Exception:
        return jsonify({"setting": result})


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
