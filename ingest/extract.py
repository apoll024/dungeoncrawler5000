"""
Extract and chunk text from PDF files.
Usage: python ingest/extract.py --pdf pdfs/PHB.pdf --source PHB --output chunks/phb.jsonl
"""
import argparse, json, sys
from pathlib import Path
import fitz  # pymupdf

CHUNK_SIZE = 1200   # characters (~300 tokens) — large enough for full rule blocks
CHUNK_OVERLAP = 150


def extract_pages(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def chunk_pages(pages: list[dict], source: str, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP) -> list[dict]:
    chunks = []
    chunk_id = 0
    for p in pages:
        text = p["text"]
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            if len(chunk_text) > 80:
                chunks.append({
                    "id": f"{source}_p{p['page']}_c{chunk_id}",
                    "text": chunk_text,
                    "source": source,
                    "page": p["page"],
                })
                chunk_id += 1
            start += chunk_size - overlap
    return chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--source", required=True, help="Book ID e.g. PHB, DMG, MM, TCE")
    parser.add_argument("--output", required=True, help="Output .jsonl file")
    args = parser.parse_args()

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    pages = extract_pages(args.pdf)
    chunks = chunk_pages(pages, args.source)

    with open(args.output, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")

    print(f"[extract] {args.source}: {len(pages)} pages → {len(chunks)} chunks → {args.output}")


if __name__ == "__main__":
    main()
