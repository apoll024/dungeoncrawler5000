"""
RAG generation: retrieve relevant passages then generate D&D content.
"""
import argparse, json, os, sys
from pathlib import Path
from typing import Generator

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from search.query import search
from ingest.db import search_chunks, search_training

LLM_API_URL   = os.getenv("LLM_API_URL", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
MODEL         = os.getenv("LLM_MODEL", "gemini-3.5-flash")
GEN_TIMEOUT   = int(os.getenv("LLM_TIMEOUT", "60"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

def _llm_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if GEMINI_API_KEY:
        h["Authorization"] = f"Bearer {GEMINI_API_KEY}"
    return h

NPC_SCHEMA = """{
  "name": str, "ancestry": str, "role": str, "appearance": str,
  "personality_traits": [str, str], "ideal": str, "bond": str, "flaw": str,
  "backstory": str, "plot_hooks": [str, str, str],
  "stat_block_suggestions": {"cr": str, "key_abilities": [str]}
}"""

MONSTER_SCHEMA = """{
  "name": str, "size": str, "type": str, "alignment": str,
  "challenge_rating": str, "xp": int, "hit_points": str, "armor_class": str, "speed": str,
  "ability_scores": {"str": int, "dex": int, "con": int, "int": int, "wis": int, "cha": int},
  "senses": str, "languages": str,
  "special_abilities": [{"name": str, "description": str}],
  "actions": [{"name": str, "description": str}],
  "description": str, "lore": str
}"""

SETTING_SCHEMA = """{
  "name": str, "premise": str, "region_type": str,
  "factions": [{"name": str, "description": str}],
  "key_conflicts": [str, str], "adventure_seeds": [str, str, str],
  "rumors": [str, str, str, str, str]
}"""

MAP_SCHEMA = """{
  "name": str,
  "theme": str,
  "rooms": [
    {
      "id": int,
      "name": str,
      "type": "entrance|corridor|room|chamber|boss|treasure|trap|stairs|secret",
      "x": int, "y": int,
      "w": int, "h": int,
      "description": str,
      "connections": [int]
    }
  ]
}"""


def _strip_json(text: str) -> str:
    """Strip markdown code fences that LLMs often wrap JSON responses in."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = text[text.index("\n") + 1:] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:text.rfind("```")]
    return text.strip()

SOURCE_POLICY = (
    "Use ONLY uploaded sourcebooks and source-derived training material stored in DC5000. "
    "Source-derived training material means summaries, categories, and reference records built from uploaded books. "
    "It is allowed. External web content, uncited general knowledge, and unsupported facts are not allowed. "
    "You may synthesize, adapt, and combine ideas across the source-derived database, including creating new NPCs, "
    "monsters, settings, and maps inspired by the uploaded books. Do not refuse just because the exact requested "
    "thing is absent; use the closest relevant source material and label invented connective tissue as source-inspired."
)


def call_llm(messages: list[dict], max_tokens: int = 1200) -> str:
    r = requests.post(
        LLM_API_URL,
        headers=_llm_headers(),
        json={"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        timeout=GEN_TIMEOUT,
    )
    if r.ok:
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError(f"LLM {r.status_code}: {r.text[:200]}")


def call_llm_streaming(messages: list[dict], max_tokens: int = 1200) -> str:
    """Collect a full streamed response from the configured OpenAI-compatible LLM."""
    r = requests.post(
        LLM_API_URL,
        headers=_llm_headers(),
        json={"model": MODEL, "messages": messages, "max_tokens": max_tokens,
              "temperature": 0.7, "stream": True},
        timeout=GEN_TIMEOUT, stream=True,
    )
    if not r.ok:
        raise RuntimeError(f"LLM {r.status_code}: {r.text[:200]}")
    parts = []
    for line in r.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8") if isinstance(line, bytes) else line
        if text.startswith("data: "):
            payload = text[6:]
            if payload.strip() == "[DONE]":
                break
            try:
                delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
                if delta:
                    parts.append(delta)
            except Exception:
                continue
    return "".join(parts)


def ask_stream(question: str, history: list[dict] = None, top_k: int = 8) -> Generator[str, None, None]:
    """Yield response tokens grounded in uploaded sourcebooks and derived training material."""
    chunks  = search(question, top_k)
    training = search_training(question, limit=max(6, top_k))
    if not chunks and not training:
        yield "No sourcebook or source-derived training material found. Please upload D&D PDFs via the Grimoire panel or rebuild the source-derived training database."
        return
    context = build_context(chunks, training)
    messages = [
        {"role": "system", "content": (
            "You are a D&D rules reference assistant. "
            + SOURCE_POLICY + " "
            "If the provided source-derived material supports a useful answer, answer normally instead of refusing. "
            "If the source database truly has no support for the topic, say what is missing."
        )},
    ]
    if history:
        messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"{question}\n\n--- DC5000 source database context ---\n{context}",
    })

    r = requests.post(
        LLM_API_URL,
        headers=_llm_headers(),
        json={"model": MODEL, "messages": messages, "max_tokens": 2000, "temperature": 0.7, "stream": True},
        timeout=GEN_TIMEOUT, stream=True,
    )
    if not r.ok:
        raise RuntimeError(f"LLM {r.status_code}: {r.text[:200]}")

    for line in r.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8") if isinstance(line, bytes) else line
        if text.startswith("data: "):
            payload = text[6:]
            if payload.strip() == "[DONE]":
                return
            try:
                delta = json.loads(payload)["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta
            except Exception:
                continue


def ask(question: str, top_k: int = 8) -> str:
    return "".join(ask_stream(question, top_k=top_k))


def retrieve_context(query: str, top_k: int, fallback_query: str) -> tuple[list[dict], list[dict]]:
    chunks = search(query, top_k) or []
    training = search_training(query, limit=max(8, top_k)) or []
    if chunks or training:
        return chunks, training

    fallback = f"{fallback_query} dungeon monster character magic combat rules lore"
    chunks = search(fallback, top_k) or []
    training = search_training(fallback, limit=max(8, top_k)) or []
    if chunks or training:
        return chunks, training

    chunks = search_chunks(fallback, limit=max(8, top_k)) or []
    if not chunks:
        for term in ("dungeon", "monster", "character", "spell", "combat", "magic", "room"):
            chunks = search_chunks(term, limit=max(8, top_k)) or []
            if chunks:
                break
    return chunks, []


def build_context(chunks: list[dict], training: list[dict] = None) -> str:
    parts = []
    if training:
        parts.append("--- Source-derived training material ---")
        parts.extend(
            f"[{t['source']}, p.{t['page']}, {t.get('kind','reference')}] {t.get('title') or 'Training item'}:\n{t['content']}"
            for t in training
        )
    if chunks:
        parts.append("--- Raw sourcebook passages ---")
        parts.extend(f"[{c['source']}, p.{c['page']}]:\n{c['text']}" for c in chunks)
    if not parts:
        return "[NO SOURCE-DERIVED MATERIAL FOUND — upload books or rebuild training material]"
    return "\n\n".join(parts)


def generate_npc(description: str, top_k: int = 6) -> str:
    query = (description or "NPC character background personality traits") + " NPC traits ancestry"
    chunks, training = retrieve_context(query, top_k, "NPC character background personality traits ancestry")
    if not chunks and not training:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks, training)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. "
            + SOURCE_POLICY + " "
            "Create by synthesizing the source-derived training material and raw passages. "
            "Return ONLY valid JSON matching this schema. Include every field, using an empty list only when needed:\n" + NPC_SCHEMA
        )},
        {"role": "user", "content": (
            f"Create a detailed NPC: {description or 'a random interesting NPC'}\n\n"
            f"--- DC5000 source database context ---\n{context}"
        )},
    ]
    return _strip_json(call_llm(messages))


def generate_monster(description: str, top_k: int = 4) -> str:
    query   = (description or "creature monster stat block abilities") + " monster CR actions abilities"
    chunks, training = retrieve_context(query, top_k, "creature monster stat block abilities CR actions")
    if not chunks and not training:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks, training)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant and monster designer. "
            + SOURCE_POLICY + " "
            "Derive stat blocks by synthesizing comparable source-derived creatures, rules, and passages. "
            "Return ONLY valid JSON matching this schema. Include every field, using empty lists only when needed:\n" + MONSTER_SCHEMA
        )},
        {"role": "user", "content": (
            f"Generate a complete 5e monster stat block: {description or 'a random unique creature'}\n\n"
            f"--- DC5000 source database context ---\n{context}"
        )},
    ]
    return _strip_json(call_llm_streaming(messages))


def generate_setting(description: str, top_k: int = 6) -> str:
    query = (description or "dungeon location region setting lore") + " location factions history"
    chunks, training = retrieve_context(query, top_k, "dungeon location region setting lore factions history")
    if not chunks and not training:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks, training)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. "
            + SOURCE_POLICY + " "
            "Build settings by synthesizing source-derived lore, factions, locations, and raw passages. "
            "Return ONLY valid JSON matching this schema. Include every field, using empty lists only when needed:\n" + SETTING_SCHEMA
        )},
        {"role": "user", "content": (
            f"Create a detailed D&D setting: {description or 'a random interesting location'}\n\n"
            f"--- DC5000 source database context ---\n{context}"
        )},
    ]
    return _strip_json(call_llm(messages))


def generate_map(description: str, top_k: int = 6) -> str:
    """Generate a 2D dungeon/location map grounded in uploaded sourcebooks."""
    query  = (description or "dungeon map rooms corridors traps encounters") + " dungeon room corridor encounter layout"
    chunks, training = retrieve_context(query, top_k, "dungeon map rooms corridors traps encounters layout")
    if not chunks and not training:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks, training)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon cartographer. "
            + SOURCE_POLICY + " "
            "Draw map structure from source-derived dungeon, encounter, trap, and location material. "
            "Generate a dungeon map as ONLY valid JSON matching this schema exactly — no markdown, no commentary:\n"
            + MAP_SCHEMA + "\n\n"
            "Rules:\n"
            "- Place all rooms on a 64×64 grid (each cell = 5 metres).\n"
            "- Use 6-12 rooms. Include entrance, corridors, at least one boss chamber.\n"
            "- Room x+w must be ≤ 64, room y+h must be ≤ 64. All values ≥ 0.\n"
            "- Rooms should not overlap. Leave corridor space between them.\n"
            "- 'connections' lists the IDs of directly adjacent/connected rooms.\n"
            "- Corridor rooms: w or h = 2, length 4-10. Chambers: w and h ≥ 4.\n"
            f"\nDC5000 source database context:\n{context}"
        )},
        {"role": "user", "content": f"Generate a dungeon map: {description or 'a random D&D dungeon'}"},
    ]
    return _strip_json(call_llm(messages, max_tokens=2500))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub    = parser.add_subparsers(dest="cmd")
    for cmd in ("ask", "npc", "monster", "setting"):
        p = sub.add_parser(cmd)
        p.add_argument("description", nargs="?", default="")
        p.add_argument("--top", type=int, default=8)
    args = parser.parse_args()
    if   args.cmd == "ask":     print(ask(args.description, args.top))
    elif args.cmd == "npc":     print(generate_npc(args.description, args.top))
    elif args.cmd == "monster": print(generate_monster(args.description, args.top))
    elif args.cmd == "setting": print(generate_setting(args.description, args.top))
    else: parser.print_help()
