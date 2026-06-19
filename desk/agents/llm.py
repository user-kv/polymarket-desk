"""
desk/agents/llm.py — the single, pluggable LLM seam.

Everything that needs a language model (brief debate, autopsy reasoning) calls
`complete()` here. Swap the brain by setting ONE env var, DESK_LLM, to one of:

  * mock   (default fallback) — deterministic, offline, zero-cost. Runs the whole
           pipeline with no key so everything is testable/dry-runnable.
  * ollama — a real open model running LOCALLY (http://localhost:11434). FREE, no
           API key, no metered credits. Best value: real reasoning at $0.
  * claude — Anthropic Messages API (Haiku cheap / Opus deep). Metered credit pool.
  * openai — OpenAI API (needs OPENAI_API_KEY).
  * gemini — Google Gemini API (needs GEMINI_API_KEY).

Auto-detect when DESK_LLM is unset: if a local Ollama is reachable, use it; else mock.
So the system is as smart as the environment allows, and never costs money unless you
deliberately point it at a paid provider.

Model routing: 'cheap' tier -> a small/fast model, 'deep' tier -> the strong model,
to respect cost (research round 4).
"""

from __future__ import annotations
import os
import json
import socket
import hashlib
import urllib.request

# ---- model routing per backend (override any of these via env) ---------------
MODELS = {
    "claude": {"cheap": os.environ.get("DESK_MODEL_CHEAP", "claude-haiku-4-5-20251001"),
               "deep":  os.environ.get("DESK_MODEL_DEEP",  "claude-opus-4-8")},
    "openai": {"cheap": os.environ.get("DESK_OPENAI_CHEAP", "gpt-4o-mini"),
               "deep":  os.environ.get("DESK_OPENAI_DEEP",  "gpt-4o")},
    "gemini": {"cheap": os.environ.get("DESK_GEMINI_CHEAP", "gemini-1.5-flash"),
               "deep":  os.environ.get("DESK_GEMINI_DEEP",  "gemini-1.5-pro")},
    "ollama": {"cheap": os.environ.get("DESK_OLLAMA_CHEAP", "qwen2:7b"),
               "deep":  os.environ.get("DESK_OLLAMA_DEEP",  "qwen2:7b")},
}
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


def _ollama_reachable(timeout=0.4) -> bool:
    try:
        host = OLLAMA_HOST.split("//")[-1].split("/")[0]
        h, _, p = host.partition(":")
        with socket.create_connection((h, int(p or 11434)), timeout=timeout):
            return True
    except OSError:
        return False


def backend() -> str:
    """Resolve the active backend. Explicit DESK_LLM wins; else auto-detect; else mock."""
    choice = os.environ.get("DESK_LLM", "").lower().strip()
    if choice in ("mock", "ollama", "claude", "openai", "gemini"):
        # guard paid backends that lack a key -> fall back rather than crash
        if choice == "claude" and not os.environ.get("ANTHROPIC_API_KEY"):
            return "mock"
        if choice == "openai" and not os.environ.get("OPENAI_API_KEY"):
            return "mock"
        if choice == "gemini" and not os.environ.get("GEMINI_API_KEY"):
            return "mock"
        return choice
    # auto: prefer a free local Ollama if it's up, else mock
    return "ollama" if _ollama_reachable() else "mock"


# ---- backends ----------------------------------------------------------------
def _mock_complete(system, user, want_json, tier) -> str:
    seed = hashlib.sha256((system + "|" + user).encode()).hexdigest()
    if not want_json:
        return f"[mock:{tier}] {user[:160]}"
    facts = {}
    if "```facts" in user:
        try:
            facts = json.loads(user.split("```facts")[1].split("```")[0].strip())
        except Exception:
            facts = {}
    return json.dumps({"_backend": "mock", "_seed": seed[:8], "facts_seen": facts})


def _ollama_complete(system, user, want_json, tier) -> str:
    model = MODELS["ollama"][tier]
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "stream": False,
        "keep_alive": "30m",      # keep the model resident between cycle calls
    }
    if want_json:
        payload["format"] = "json"
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    # generous timeout: a cold 4-7GB model load on CPU can take a few minutes
    with urllib.request.urlopen(req, timeout=420) as resp:
        data = json.loads(resp.read())
    return data.get("message", {}).get("content", "")


def _claude_complete(system, user, want_json, tier) -> str:
    from anthropic import Anthropic  # lazy
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=MODELS["claude"][tier], max_tokens=1024,
        system=system + ("\nRespond with strict JSON only." if want_json else ""),
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def _openai_complete(system, user, want_json, tier) -> str:
    from openai import OpenAI  # lazy
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    kw = {"response_format": {"type": "json_object"}} if want_json else {}
    r = client.chat.completions.create(
        model=MODELS["openai"][tier],
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        max_tokens=1024, **kw)
    return r.choices[0].message.content


def _gemini_complete(system, user, want_json, tier) -> str:
    import google.generativeai as genai  # lazy
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    cfg = {"response_mime_type": "application/json"} if want_json else {}
    model = genai.GenerativeModel(MODELS["gemini"][tier], system_instruction=system,
                                  generation_config=cfg)
    return model.generate_content(user).text


_DISPATCH = {"mock": _mock_complete, "ollama": _ollama_complete, "claude": _claude_complete,
             "openai": _openai_complete, "gemini": _gemini_complete}


def complete(system: str, user: str, want_json: bool = False, tier: str = "cheap") -> str:
    """tier: 'cheap' for routine extraction, 'deep' for debate/autopsy."""
    b = backend()
    try:
        return _DISPATCH[b](system, user, want_json, tier)
    except Exception as e:
        # any provider hiccup degrades to the deterministic mock rather than crashing the loop
        return _mock_complete(system, user, want_json, tier) if b != "mock" else \
            json.dumps({"_backend": "mock", "_error": str(e)[:120]})


if __name__ == "__main__":
    print("active backend:", backend())
    print(complete("You are a test.", "ping ```facts\n{\"x\":1}\n```", want_json=True, tier="deep"))
