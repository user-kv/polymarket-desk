"""
desk/config.py — tiny zero-dependency .env loader.

Secrets (API keys) live ONLY in desk/.env, never in any config.json and never in
git (desk/.env is covered by the root .gitignore `.env` rule). Importing this module
loads desk/.env into os.environ for keys that are not already set, so:

  * locally:   put GEMINI_API_KEY=... in desk/.env and everything picks it up,
  * in CI/VPS: real environment variables / GitHub Secrets win (we never overwrite
    an already-set var), so nothing leaks into the repo.

No external dependency (python-dotenv is intentionally avoided so the desk stays
installable with the standard library only).
"""

from __future__ import annotations
import os
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_env(path: Path = ENV_PATH) -> dict:
    """Load KEY=VALUE lines from desk/.env into os.environ (without overwriting).

    Returns the dict of keys it set, for debugging. Silent no-op if the file is
    absent — the system must run fine with no .env at all (falls back to mock).
    """
    loaded: dict[str, str] = {}
    if not path.exists():
        return loaded
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        # strip optional surrounding quotes and inline trailing comments are NOT
        # stripped (a value may legitimately contain '#'); keep it literal.
        val = val.strip().strip('"').strip("'")
        # Skip empty values: an unfilled `GEMINI_API_KEY=` must leave the var unset
        # (not injected as "") so backend auto-detect treats it as "no key yet".
        if key and val and key not in os.environ:
            os.environ[key] = val
            loaded[key] = val
    return loaded


# Load on import so any module that does `from desk import config` (or imports the
# llm seam, which imports this) gets the .env applied exactly once.
_LOADED = load_env()


if __name__ == "__main__":
    present = {k: ("set" if os.environ.get(k) else "missing") for k in
               ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DESK_LLM")}
    print(f".env path: {ENV_PATH}  (exists={ENV_PATH.exists()})")
    print(f"keys loaded from .env this run: {sorted(_LOADED)}")
    print("relevant vars:", present)
