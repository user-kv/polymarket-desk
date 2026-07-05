"""Provider-agnostic LLM seam (CONSTITUTION §11B model routing).

Routing is declared as DATA here so it is auditable and swappable without
touching callers. The mock default keeps tests fully offline and deterministic.

Live providers (2026-07-06, per Opus research pass — see FABLE5/out/CHANGELOG):
  PRIMARY   Groq free tier (llama-3.3-70b-versatile, 1,000 req/day; no
            production-use prohibition in ToS). Key: GROQ_API_KEY env var.
  FALLBACK  OpenRouter (OPENROUTER_API_KEY) — same OpenAI-compatible shape.
  REJECTED  NVIDIA NIM free tier — its Trial ToS bars production use.
Forecast calls use temperature=0 and ask for JSON; callers must validate.
"""
import json
import os
import time
import urllib.error
import urllib.request

ROUTING = {
    "reason":    "claude-opus-4-8",      # strategy-gen, red-team, allocator
    "judge":     "claude-opus-4-8",      # mechanism judging
    "classify":  "llama-3.1-8b-instant",
    "index":     "llama-3.1-8b-instant",
    "forecast":  "llama-3.3-70b-versatile",  # Alpha Engine swarm workers (A6)
    "supervise": "claude-opus-4-8",      # Alpha Engine supervisor reconciliation (A6)
}

_PROVIDERS = [
    # (env key, base url) — tried in order; first with a key present wins.
    ("GROQ_API_KEY", "https://api.groq.com/openai/v1/chat/completions"),
    ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1/chat/completions"),
]


def _live_complete(prompt, model, max_tokens, temperature):
    last_err = None
    for env_key, url in _PROVIDERS:
        key = os.environ.get(env_key, "").strip()
        if not key:
            continue
        body = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        })
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read().decode("utf-8"))
                return out["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                last_err = e
                if e.code in (429, 500, 502, 503):
                    time.sleep(2 ** attempt)
                    continue
                break
            except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
                last_err = e
                time.sleep(2 ** attempt)
    raise RuntimeError(f"no live LLM provider available (set GROQ_API_KEY); last: {last_err}")


def complete(prompt, role="reason", mock=True, max_tokens=512, temperature=0.0, **kw) -> str:
    """Call an LLM with role-based model routing.

    mock=True (default and in all tests): returns a deterministic stub keyed
    off role so callers have a stable contract without network access.
    mock=False: dispatches ROUTING[role] to the first configured provider
    (Groq primary, OpenRouter fallback). Anthropic-model roles (reason/judge/
    supervise) are NOT wired to the free tier — they raise, deliberately:
    judgment seats are not delegated to a free 70B model by accident.
    """
    if mock:
        return f"[MOCK:{role}] ok"
    model = ROUTING.get(role, ROUTING["reason"])
    if model.startswith("claude-"):
        raise RuntimeError(
            f"role '{role}' routes to {model}, which has no free-tier wiring; "
            "judgment roles stay mock/manual until a paid provider is approved (O2)")
    return _live_complete(prompt, model, max_tokens, temperature)
