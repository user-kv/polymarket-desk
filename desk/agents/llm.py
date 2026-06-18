"""
desk/agents/llm.py — the single, pluggable LLM seam.

Everything that needs a language model (brief debate, autopsy reasoning) calls
`complete()` here. There are two backends:

  * MOCK (default): a deterministic, offline reasoner. Costs nothing, needs no API
    key, and makes the whole pipeline runnable + unit-testable in CI. It returns
    structured, plausible output derived from the inputs.

  * CLAUDE: the real Claude Agent SDK / Messages API. Activated only when
    DESK_LLM=claude AND an ANTHROPIC_API_KEY is present. Model routing (research
    round 4): cheap subtasks -> Haiku, debate/autopsy -> Opus, to respect the
    post-June-15-2026 metered credit pool.

Switching mock -> real is ONE of the two human steps to go live (the other is the
cloud account). No code change is needed — just set the env vars.
"""

from __future__ import annotations
import os
import json
import hashlib

# Model routing for the real backend (only used when DESK_LLM=claude).
MODEL_CHEAP = os.environ.get("DESK_MODEL_CHEAP", "claude-haiku-4-5-20251001")
MODEL_DEEP = os.environ.get("DESK_MODEL_DEEP", "claude-opus-4-8")


def backend() -> str:
    if os.environ.get("DESK_LLM", "mock").lower() == "claude" and os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    return "mock"


def _mock_complete(system: str, user: str, want_json: bool, tier: str) -> str:
    """
    Deterministic stand-in. Produces stable JSON keyed off the input hash so tests
    and dry-runs are reproducible. It is intentionally simple: it surfaces the
    structured fields the callers expect without pretending to be smart.
    """
    seed = hashlib.sha256((system + "|" + user).encode()).hexdigest()
    if not want_json:
        return f"[mock:{tier}] {user[:160]}"
    # Heuristics: callers embed a JSON 'facts' block we echo/lightly transform.
    facts = {}
    if "```facts" in user:
        try:
            facts = json.loads(user.split("```facts")[1].split("```")[0].strip())
        except Exception:
            facts = {}
    out = {
        "_backend": "mock",
        "_seed": seed[:8],
        "facts_seen": facts,
    }
    return json.dumps(out)


def _claude_complete(system: str, user: str, want_json: bool, tier: str) -> str:
    """Real backend. Imported lazily so the mock path needs no SDK installed."""
    from anthropic import Anthropic  # type: ignore
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = MODEL_DEEP if tier == "deep" else MODEL_CHEAP
    msg = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system + ("\nRespond with strict JSON only." if want_json else ""),
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def complete(system: str, user: str, want_json: bool = False, tier: str = "cheap") -> str:
    """
    tier: 'cheap' (Haiku) for routine extraction, 'deep' (Opus) for debate/autopsy.
    Returns the model's text (a JSON string if want_json).
    """
    if backend() == "claude":
        return _claude_complete(system, user, want_json, tier)
    return _mock_complete(system, user, want_json, tier)
