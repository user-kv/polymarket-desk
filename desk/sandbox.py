"""
desk/sandbox.py — execute self-written tools under containment (research round 3).

The 2026 reports are blunt: "polite" in-process sandboxes get bypassed. So a new
self-written tool faces two barriers before it is ever trusted:

  1. STATIC ANALYSIS (AST) — reject the tool outright if its source imports or calls
     anything dangerous: os.system, subprocess, socket, eval/exec, open(...,'w') for
     paths outside the sandbox, __import__, ctypes, etc. This is enforceable and runs
     with zero execution risk.

  2. ISOLATED EXECUTION — run it in a separate Python subprocess with a stripped
     environment, a temp working dir, and a hard timeout. On the Linux VPS this same
     entry point is additionally run as a restricted, network-firewalled user
     (allowlist only) for defense in depth — see desk/deploy/.

A tool that fails either barrier never enters the live loop.
"""

from __future__ import annotations
import ast
import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Imports a sandboxed tool may NOT use.
_BANNED_IMPORTS = {"os", "subprocess", "socket", "ctypes", "shutil", "multiprocessing",
                   "threading", "pickle", "marshal", "importlib", "pty", "signal"}
# Allowed safe imports for a data-fetching tool.
_ALLOWED_IMPORTS = {"json", "math", "statistics", "datetime", "urllib", "urllib.request",
                    "urllib.parse", "re", "typing", "dataclasses", "collections"}
# Dangerous bare names / calls.
_BANNED_CALLS = {"eval", "exec", "compile", "__import__", "open", "input", "globals",
                 "locals", "vars", "getattr", "setattr", "delattr"}


class StaticAnalysisError(Exception):
    pass


def static_analyze(source: str) -> tuple[bool, str]:
    """AST scan. Returns (ok, reason). ok=False means reject without executing."""
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, f"syntax error: {e}"

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in _BANNED_IMPORTS:
                    return False, f"banned import: {a.name}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _BANNED_IMPORTS:
                return False, f"banned import-from: {node.module}"
        elif isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if name in _BANNED_CALLS:
                return False, f"banned call: {name}()"
        elif isinstance(node, ast.Attribute):
            if node.attr in ("system", "popen", "fork", "spawn", "remove", "unlink", "rmtree"):
                return False, f"banned attribute access: .{node.attr}"
    return True, "static analysis clean"


def run_tool(source: str, entry: str = "run", args_json: str = "{}",
             timeout: int = 20) -> dict:
    """
    Static-analyze, then execute the tool's `entry(**args)` in an isolated subprocess.
    Returns {ok, stdout, stderr, returncode, rejected?}.
    """
    ok, reason = static_analyze(source)
    if not ok:
        return {"ok": False, "rejected": True, "reason": reason}

    harness = (
        source
        + "\n\nif __name__ == '__main__':\n"
        + "    import json, sys\n"
        + f"    _a = json.loads({args_json!r})\n"
        + f"    _r = {entry}(**_a) if isinstance(_a, dict) else {entry}(_a)\n"
        + "    print(json.dumps({'result': _r}, default=str))\n"
    )

    workdir = Path(tempfile.mkdtemp(prefix="desk_sbx_"))
    script = workdir / "tool.py"
    script.write_text(harness, encoding="utf-8")

    # stripped environment: no inherited secrets, isolation flag set
    safe_env = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                "DESK_SANDBOX": "1", "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run(
            [sys.executable, "-I", str(script)],   # -I: isolated mode, ignore env/user site
            cwd=str(workdir), env=safe_env, capture_output=True, text=True,
            timeout=timeout,
        )
        return {"ok": proc.returncode == 0, "rejected": False,
                "returncode": proc.returncode, "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip()}
    except subprocess.TimeoutExpired:
        return {"ok": False, "rejected": False, "reason": f"timeout >{timeout}s"}
    finally:
        try:
            script.unlink()
            workdir.rmdir()
        except OSError:
            pass


if __name__ == "__main__":
    clean = "def run():\n    import math\n    return math.sqrt(16)\n"
    dirty = "import os\ndef run():\n    return os.system('echo hacked')\n"
    print("clean:", run_tool(clean))
    print("dirty:", run_tool(dirty))
