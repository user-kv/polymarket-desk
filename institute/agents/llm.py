"""Provider-agnostic LLM seam (CONSTITUTION §11B model routing).

Routing is declared as DATA here so it is auditable and swappable without
touching callers. The mock default keeps tests fully offline and deterministic.
"""

ROUTING = {
    "reason":    "claude-opus-4-8",      # strategy-gen, red-team, allocator
    "judge":     "claude-opus-4-8",      # mechanism judging
    "classify":  "claude-haiku-4-5",
    "index":     "claude-haiku-4-5",
    "forecast":  "claude-sonnet-4-6",   # Alpha Engine swarm workers (A6)
    "supervise": "claude-opus-4-8",     # Alpha Engine supervisor reconciliation (A6)
}


def complete(prompt, role="reason", mock=True, **kw) -> str:
    """Call an LLM with role-based model routing.

    mock=True (default and in all tests): returns a deterministic stub keyed
    off role so callers have a stable contract without network access.

    TODO: wire real providers behind this signature by setting mock=False and
    dispatching to the model named in ROUTING[role]. Each provider client
    should be imported lazily here so the seam is the only place that changes.
    Example stub:
        if not mock:
            import anthropic
            client = anthropic.Anthropic()
            msg = client.messages.create(
                model=ROUTING.get(role, ROUTING["reason"]),
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
    """
    return f"[MOCK:{role}] ok"
