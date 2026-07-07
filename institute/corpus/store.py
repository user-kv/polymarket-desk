"""Append-only JSONL store (source of truth). Rebuild = reload (CONSTITUTION §2 data plane)."""
import os
import json


def append_jsonl(path, records):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # tolerate one truncated trailing line (crash mid-append) rather
                # than wedging every future snapshot/settle run
                continue
    return out


def overwrite_jsonl(path, records):
    # atomic: this store is the declared source of truth; a crash mid-rewrite
    # must not truncate it (settle() calls this every cron tick)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, path)
