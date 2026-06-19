# Hosting the desk (laptop-independent)

Goal: the scan + learning loop run 24/7 without your laptop being open.
**Fake money only** — no wallet, no exchange keys, ever.

Now that the reasoning brain is a **Gemini API call** (not a local model), there's no
heavy compute to host — the job is a short Python script a few times a day. That makes
the simplest, cheapest option also the best:

---

## ✅ Recommended: GitHub Actions (free, no server, no credit card)

Two scheduled workflows are already in `.github/workflows/`:
- **desk-scan.yml** — scan + settle every hour at :40 UTC (24×/day; hits model-run latency
  edge on 00/06/12/18Z), commits the ledger back.
- **desk-cycle.yml** — full reflective cycle daily at 14:15 UTC (autopsy → lessons →
  consolidate into Second-Brain principles → briefs → digest), commits grown memory back.

Why this wins for *this* system:
| | GitHub Actions | Oracle/Hetzner VPS |
|---|---|---|
| Cost | $0 (2,000 min/mo private; our jobs use ~minutes/day) | $0–3.79/mo |
| Credit card | **none** | required (even for "always free") |
| Server to maintain | **none** | yes (patching, timers, SSH) |
| Secrets | GitHub Secrets | `.env` on the box |
| Laptop-independent | ✅ | ✅ |

### Setup — the only steps that need you (≈5 minutes, one time)
1. **Create a GitHub repo and push** (the project is already a git repo locally):
   ```bash
   gh repo create polymarket-desk --private --source . --remote origin --push
   # or: make a repo in the UI, then `git remote add origin … && git push -u origin master`
   ```
   Scheduled workflows run on the **default branch** only.
2. **Add the free Gemini key as a repo secret** (optional but recommended — it's what
   makes the desk *self-learning* instead of running the heuristic):
   - get a key (Google account, ~60s, **no card**): https://aistudio.google.com/apikey
   - repo → **Settings → Secrets and variables → Actions → New repository secret**
   - name `GEMINI_API_KEY`, paste the value.
3. That's it. Watch the **Actions** tab; trigger a run now with **Run workflow**
   (`workflow_dispatch`) to confirm. Memory and digest commit straight back to the repo.

> Note: GitHub auto-pauses scheduled workflows after 60 days of **repo inactivity**.
> Our jobs commit on every run, so activity is continuous — but if you ever pause, a
> single push or manual run re-arms the schedule.

---

## Local fallback: Windows Task Scheduler (already installed)
`desk/deploy/setup_local_windows.ps1` registers `PolymarketDesk-Scan` (every 6h) and
`PolymarketDesk-Cycle` (daily). Runs whenever this PC is awake — good as a backup or if
you don't want a GitHub repo. It auto-commits data after each scan (data safety net).

## Heavy fallback: a real VPS (only if you later run a *local* model)
Oracle Cloud Always Free (4 ARM / 24 GB, $0) or Hetzner CAX11 (~$3.79/mo). `setup_vps.sh`
installs deps, baselines the kernel, runs the tests, and enables two systemd user timers
(`papertrader-scan.timer`, `desk-cycle.timer`). Only worth it if you switch `DESK_LLM`
to a self-hosted Ollama and need the RAM — with Gemini you don't.

---

## The brain (how reasoning is chosen)
Set in `desk/.env` (local) or as the `GEMINI_API_KEY` secret (CI). Auto-detect:
`gemini` if a key is present → else the deterministic **heuristic** (free, offline,
always works). Ollama is opt-in via `DESK_LLM=ollama` (too slow on a typical laptop).

- Free Gemini quota is ~1,500 requests/day on Flash models — far more than the desk
  uses. No credit card, no expiry.
- Optional paid brains (`claude`, `openai`) are wired but off; they bill at API rates.

## Operating it
- Watch what it does: `desk/digest_latest.md`.
- Self-modification is **OFF by default** (`selfmod_config.json` kill switch). After
  ≥30 resolved bets and digests you trust, you *may* set `self_modification_enabled: true`.
  Kill it instantly by setting it back to `false`.
- Undo any self-written change: `git revert <commit>` (each change is its own commit).
