"""
RAG generation: retrieve relevant passages then generate D&D content.
Usage:
    python generate/generate.py ask "How does grappling work?"
    python generate/generate.py npc "A disgraced city guard turned bounty hunter"
    python generate/generate.py setting "Coastal town plagued by a drowned god"
"""
import argparse, json, os, sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from search.query import search

COPILOT_API_URL = os.getenv("COPILOT_API_URL", "https://api.githubcopilot.com/chat/completions")
COPILOT_OAUTH_TOKEN = os.getenv("COPILOT_OAUTH_TOKEN", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
FALLBACK_URL = os.getenv("COPILOT_FALLBACK_API_URL", "https://models.github.ai/inference/chat/completions")
MODEL = os.getenv("COPILOT_MODEL", "gpt-4o-mini")

NPC_SCHEMA = """{
  "name": str,
  "ancestry": str,
  "role": str,
  "appearance": str,
  "personality_traits": [str, str],
  "ideal": str,
  "bond": str,
  "flaw": str,
  "backstory": str,
  "plot_hooks": [str, str, str],
  "stat_block_suggestions": {"cr": str, "key_abilities": [str]}
}"""

SETTING_SCHEMA = """{
  "name": str,
  "premise": str,
  "region_type": str,
  "factions": [{"name": str, "description": str}],
  "key_conflicts": [str, str],
  "adventure_seeds": [str, str, str],
  "rumors": [str, str, str, str, str]
}"""


def call_llm(messages: list[dict]) -> str:
    endpoints = []
    if COPILOT_OAUTH_TOKEN:
        endpoints.append((COPILOT_API_URL, COPILOT_OAUTH_TOKEN, "copilot"))
    if GITHUB_TOKEN:
        endpoints.append((FALLBACK_URL, GITHUB_TOKEN, "github_models"))

    for url, token, kind in endpoints:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if kind == "copilot":
            headers["Copilot-Integration-Id"] = "vscode-chat"
            headers["Editor-Version"] = "vscode/1.90.0"
        else:
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        try:
            r = requests.post(url, headers=headers,
                              json={"model": MODEL, "messages": messages, "max_tokens": 2000, "temperature": 0.7},
                              timeout=30)
            if r.ok:
                return r.json()["choices"][0]["message"]["content"]
            print(f"  [{kind}] {r.status_code}: {r.text[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"  [{kind}] error: {e}", file=sys.stderr)

    raise RuntimeError("All LLM endpoints failed.")


def build_context(chunks: list[dict]) -> str:
    return "\n\n".join(
        f"[{c['source']}, p.{c['page']}]:\n{c['text']}"
        for c in chunks
    )


def ask(question: str, top_k: int = 8) -> str:
    chunks = search(question, top_k)
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D rules reference assistant. "
            "Answer using ONLY the exact text from the provided source passages. "
            "Quote the relevant rules directly and cite the source as (Book, p.N). "
            "Do not add interpretation beyond what the text states."
        )},
        {"role": "user", "content": f"Question: {question}\n\nSource passages:\n{context}"}
    ]
    return call_llm(messages)


def generate_npc(description: str, top_k: int = 6) -> str:
    chunks = search(description + " NPC character traits background", top_k)
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. "
            "Use the provided sourcebook passages to ground the NPC in official lore and mechanics. "
            "Reference specific rules or lore where relevant (cite source + page). "
            "Return valid JSON matching this schema:\n" + NPC_SCHEMA
        )},
        {"role": "user", "content": f"Create a detailed NPC: {description}\n\nSourcebook passages:\n{context}"}
    ]
    return call_llm(messages)


def generate_setting(description: str, top_k: int = 6) -> str:
    chunks = search(description + " location region setting lore", top_k)
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": (
            "You are a D&D dungeon master assistant. "
            "Use the provided sourcebook passages to ground the setting in official lore and mechanics. "
            "Reference specific rules or lore where relevant (cite source + page). "
            "Return valid JSON matching this schema:\n" + SETTING_SCHEMA
        )},
        {"role": "user", "content": f"Create a detailed setting: {description}\n\nSourcebook passages:\n{context}"}
    ]
    return call_llm(messages)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("ask"); p.add_argument("question"); p.add_argument("--top", type=int, default=8)
    p = sub.add_parser("npc"); p.add_argument("description"); p.add_argument("--top", type=int, default=6)
    p = sub.add_parser("setting"); p.add_argument("description"); p.add_argument("--top", type=int, default=6)

    args = parser.parse_args()
    if args.cmd == "ask":
        print(ask(args.question, args.top))
    elif args.cmd == "npc":
        print(generate_npc(args.description, args.top))
    elif args.cmd == "setting":
        print(generate_setting(args.description, args.top))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
