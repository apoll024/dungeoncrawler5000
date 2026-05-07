"""Flask API for dungeoncrawler5000."""
import json, os, sys
from pathlib import Path

from flask import Flask, request, jsonify

sys.path.insert(0, str(Path(__file__).parent.parent))
from search.query import search
from generate.generate import ask, generate_npc, generate_setting
from ingest.extract import extract_pages, chunk_pages
from ingest.embed import embed_chunks

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/search", methods=["POST"])
def search_route():
    data = request.json
    results = search(data.get("query", ""), data.get("top", 8), data.get("source"))
    return jsonify({"results": results})


@app.route("/ask", methods=["POST"])
def ask_route():
    data = request.json
    return jsonify({"answer": ask(data.get("question", ""), data.get("top", 8))})


@app.route("/generate/npc", methods=["POST"])
def npc_route():
    data = request.json
    result = generate_npc(data.get("description", ""), data.get("top", 6))
    try:
        return jsonify({"npc": json.loads(result)})
    except Exception:
        return jsonify({"npc": result})


@app.route("/generate/setting", methods=["POST"])
def setting_route():
    data = request.json
    result = generate_setting(data.get("description", ""), data.get("top", 6))
    try:
        return jsonify({"setting": json.loads(result)})
    except Exception:
        return jsonify({"setting": result})


@app.route("/ingest", methods=["POST"])
def ingest_route():
    data = request.json
    pdf_path = data.get("pdf_path")
    source = data.get("source")
    if not pdf_path or not source:
        return jsonify({"error": "pdf_path and source required"}), 400
    pages = extract_pages(pdf_path)
    chunks = chunk_pages(pages, source)
    embed_chunks(chunks)
    return jsonify({"status": "ok", "pages": len(pages), "chunks": len(chunks)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
