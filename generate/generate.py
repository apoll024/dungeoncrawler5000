"""
RAG generation: retrieve relevant passages then generate D&D content.
"""
import argparse, json, os, sys
from pathlib import Path
from typing import Generator

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from search.query import search

LLM_API_URL = os.getenv("LLM_API_URL", "http://ollama:11434/v1/chat/completions")
MODEL       = os.getenv("LLM_MODEL", "llama3.2:3b")
GEN_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))

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


def call_llm(messages: list[dict], max_tokens: int = 1200) -> str:
    r = requests.post(
        LLM_API_URL,
        headers={"Content-Type": "application/json"},
        json={"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        timeout=GEN_TIMEOUT,
    )
    if r.ok:
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError(f"LLM {r.status_code}: {r.text[:200]}")


def ask_stream(question: str, history: list[dict] = None, top_k: int = 8) -> Generator[str, None, None]:
    """Yield response tokens as a streaming SSE generator."""
    chunks   = search(question, top_k)
    context  = "\n\n".join(f"[{c['source']}, p.{c['page']}]:\n{c['text']}" for c in chunks)
    messages = [
        {"role": "system", "content": (
            "You are a knowledgeable D&D rules reference assistant and storyteller. "
            "Answer using the provided sourcebook passages as your primary reference. "
            "Cite sources as (Book, p.N) when quoting rules. "
            "Be helpful, evocative, and accurate to the official D&D 5e rules."
        )},
    ]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": f"{question}\n\n--- Source passages ---\n{context}"})

    r = requests.post(
        LLM_API_URL,
        headers={"Content-Type": "application/json"},
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
    return "\n\n".join(f"[{c['source']}, p.{c['page']}]:\n{c['text']}" for c in chunks)


def generate_npc(description: str, top_k: int = 6) -> str:
    chunks   = search((description or "interesting NPC character background") + " NPC traits", top_k)
    context  = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. Ground the NPC in official lore and mechanics. "
            "Cite source + page where relevant. Return ONLY valid JSON matching this schema:\n" + NPC_SCHEMA
        )},
        {"role": "user", "content": f"Create a detailed NPC: {description or 'a random interesting NPC'}\n\nSourcebook passages:\n{context}"},
    ]
    return call_llm(messages)


def generate_monster(description: str, top_k: int = 4) -> str:
    query    = (description or "random creature monster stat block") + " monster abilities actions CR"
    chunks   = search(query, top_k)
    context  = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant and monster designer. "
            "Use the sourcebook passages to ground the creature in official lore and 5e mechanics. "
            "Follow 5e monster design conventions for ability scores, CR, and action economy. "
            "Return ONLY valid JSON matching this schema:\n" + MONSTER_SCHEMA
        )},
        {"role": "user", "content": f"Generate a complete monster stat block: {description or 'a random unique creature'}\n\nSourcebook passages:\n{context}"},
    ]
    return call_llm(messages)


def generate_setting(description: str, top_k: int = 6) -> str:
    chunks   = search((description or "dungeon location setting") + " location region lore", top_k)
    context  = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. Ground the setting in official lore. "
            "Return ONLY valid JSON matching this schema:\n" + SETTING_SCHEMA
        )},
        {"role": "user", "content": f"Create a detailed setting: {description or 'a random interesting location'}\n\nSourcebook passages:\n{context}"},
    ]
    return call_llm(messages)


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
