"""
RAG generation: retrieve relevant passages then generate D&D content.
"""
import argparse, json, os, sys
from pathlib import Path
from typing import Generator

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from search.query import search

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
    """Yield response tokens. Answers ONLY from uploaded sourcebook passages."""
    chunks  = search(question, top_k)
    if not chunks:
        yield "No sourcebook passages found. Please upload your D&D PDFs via the Grimoire panel. The Oracle answers ONLY from your uploaded books."
        return
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D rules reference assistant. "
            "You MUST answer ONLY from the sourcebook passages provided. "
            "Cite every rule as (Source, p.N). "
            "You are STRICTLY PROHIBITED from using any general knowledge or training data. "
            "If asked about something not covered in the passages, say so explicitly."
        )},
    ]
    if history:
        messages.extend(history)
    messages.append({
        "role": "user",
        "content": f"{question}\n\n--- Sourcebook passages (answer ONLY from these) ---\n{context}",
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


def build_context(chunks: list[dict]) -> str:
    if not chunks:
        return "[NO PASSAGES FOUND — no books have been uploaded to the Grimoire yet]"
    return "\n\n".join(f"[{c['source']}, p.{c['page']}]:\n{c['text']}" for c in chunks)


def generate_npc(description: str, top_k: int = 6) -> str:
    chunks  = search((description or "NPC character background personality traits") + " NPC traits ancestry", top_k)
    if not chunks:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. "
            "You MUST base your answer ONLY on the sourcebook passages provided below. "
            "Do not use outside knowledge. Cite (Source, p.N) for every detail you draw from. "
            "If no relevant passages were found, say so explicitly and refuse to fabricate. "
            "Return ONLY valid JSON matching this schema:\n" + NPC_SCHEMA
        )},
        {"role": "user", "content": (
            f"Create a detailed NPC: {description or 'a random interesting NPC'}\n\n"
            f"--- Sourcebook passages (use ONLY these) ---\n{context}"
        )},
    ]
    return _strip_json(call_llm(messages))


def generate_monster(description: str, top_k: int = 4) -> str:
    query   = (description or "creature monster stat block abilities") + " monster CR actions abilities"
    chunks  = search(query, top_k)
    if not chunks:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant and monster designer. "
            "You MUST ground every value (HP, CR, ability scores, actions) in the sourcebook passages provided. "
            "Do not invent stats from scratch — derive them from the passages. "
            "Cite (Source, p.N) in the description/lore fields. "
            "If no relevant passages were found, say so and refuse to fabricate. "
            "Return ONLY valid JSON matching this schema:\n" + MONSTER_SCHEMA
        )},
        {"role": "user", "content": (
            f"Generate a complete 5e monster stat block: {description or 'a random unique creature'}\n\n"
            f"--- Sourcebook passages (use ONLY these) ---\n{context}"
        )},
    ]
    return _strip_json(call_llm_streaming(messages))


def generate_setting(description: str, top_k: int = 6) -> str:
    chunks  = search((description or "dungeon location region setting lore") + " location factions history", top_k)
    if not chunks:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. "
            "You MUST base the setting ONLY on the sourcebook passages provided. "
            "Cite (Source, p.N) in the premise and faction descriptions. "
            "If no relevant passages were found, say so and refuse to fabricate. "
            "Return ONLY valid JSON matching this schema:\n" + SETTING_SCHEMA
        )},
        {"role": "user", "content": (
            f"Create a detailed D&D setting: {description or 'a random interesting location'}\n\n"
            f"--- Sourcebook passages (use ONLY these) ---\n{context}"
        )},
    ]
    return _strip_json(call_llm(messages))


def generate_map(description: str, top_k: int = 6) -> str:
    """Generate a 2D dungeon/location map grounded in uploaded sourcebooks."""
    query  = (description or "dungeon map rooms corridors traps encounters") + " dungeon room corridor encounter layout"
    chunks = search(query, top_k)
    if not chunks:
        raise RuntimeError("No sourcebook passages found. Upload your D&D PDFs via the Grimoire panel first.")
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon cartographer. "
            "Draw inspiration from the sourcebook passages provided. "
            "Cite (Source, p.N) in room descriptions. "
            "Generate a dungeon map as ONLY valid JSON matching this schema exactly — no markdown, no commentary:\n"
            + MAP_SCHEMA + "\n\n"
            "Rules:\n"
            "- Place all rooms on a 64×64 grid (each cell = 5 metres).\n"
            "- Use 6-12 rooms. Include entrance, corridors, at least one boss chamber.\n"
            "- Room x+w must be ≤ 64, room y+h must be ≤ 64. All values ≥ 0.\n"
            "- Rooms should not overlap. Leave corridor space between them.\n"
            "- 'connections' lists the IDs of directly adjacent/connected rooms.\n"
            "- Corridor rooms: w or h = 2, length 4-10. Chambers: w and h ≥ 4.\n"
            f"\nSourcebook passages:\n{context}"
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
