"""Independent analytical lenses for the Alpha Engine swarm (A6).

Five fixed personas. Independence + diversity beats a bigger homogeneous pool
(PolySwarm research: no inter-agent communication to prevent anchoring).

The ``lean`` field is ONLY used by the deterministic mock to spread the
ensemble realistically; the real (mock=False) path ignores it and uses the
prompt text.  Keep |lean| small.
"""

PERSONAS = [
    {
        "id": "base_rate",
        "lean": 0.00,
        "prompt": (
            "Forecast purely from the historical base rate for this class of event. "
            "Ignore narrative."
        ),
    },
    {
        "id": "contrarian",
        "lean": -0.08,
        "prompt": (
            "Assume the crowd is over-reacting to recent news. Fade the consensus."
        ),
    },
    {
        "id": "mechanism",
        "lean": 0.00,
        "prompt": (
            "Reason from the concrete causal mechanism that resolves this market."
        ),
    },
    {
        "id": "recency",
        "lean": +0.05,
        "prompt": (
            "Weight the most recent signal heavily; momentum tends to persist "
            "short-horizon."
        ),
    },
    {
        "id": "skeptic",
        "lean": -0.05,
        "prompt": (
            "Demand strong evidence for any YES; default toward the cheaper, safer side."
        ),
    },
]
