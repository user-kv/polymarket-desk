# Deploying the desk to a cloud VPS (laptop-independent)

Goal: the scan + learning loop run 24/7 without your laptop. **Fake money only** —
no wallet, no exchange keys, ever.

## Pick a host
| | Primary: **Oracle Cloud Always Free** | Fallback: **Hetzner CAX11** |
|---|---|---|
| Cost | $0 forever | ~$3.79/mo |
| Specs | 4 ARM cores / 24 GB RAM | 2 ARM / 4 GB |
| Catch | reclaims *idle* free instances; the scheduled timers keep it active | none — rock solid |

Both are Ubuntu ARM; the setup is identical. The server is rounding error next to the
LLM credits — the cost control that matters is in `desk/agents/llm.py` (Haiku for
cheap subtasks, Opus only for debate/autopsy) and the caps in `selfmod_config.json`.

## Steps
1. Create the VPS (Ubuntu 22.04+ ARM). SSH in.
2. Copy the project up (or `git clone` your repo) to `~/polymarket`.
   ```bash
   rsync -av --exclude .git ./polymarket/ user@vps:~/polymarket/
   ```
3. Run the provisioner:
   ```bash
   bash ~/polymarket/desk/deploy/setup_vps.sh
   ```
   It installs deps, baselines the kernel, runs all tests, and enables two systemd
   user timers:
   - `papertrader-scan.timer` → scan+settle at 00/06/12/18:40 UTC (model-run latency edge)
   - `desk-cycle.timer` → reflective cycle daily 14:15 UTC (autopsy, briefs, digest)

## The two human steps (the only things I can't do for you)
1. **Make the LLM real.** Create `~/polymarket/desk/.env`:
   ```
   DESK_LLM=claude
   ANTHROPIC_API_KEY=sk-ant-...
   ```
   Until then it runs on the deterministic **mock** backend (zero cost, fully
   functional pipeline). NB the June 15 2026 billing change: Agent-SDK / headless
   usage bills from a **separate credit pool at API rates** ($20 Pro / $100 Max5x /
   $200 Max20x), not your subscription — budget the ~$5/day against that.
2. **Enable self-modification** (optional, later). It is **OFF by default**. After
   ≥30 resolved bets and a few digests you trust, set
   `"self_modification_enabled": true` in `desk/selfmod_config.json`.

## Operating it
- Watch what it does: `cat ~/polymarket/desk/digest_latest.md`
- Kill self-mod instantly: set `self_modification_enabled=false` (one word).
- Undo any self-written change: `git revert <commit>` (every change is its own commit).
- Prefect (optional, nicer observability for the reflective loop):
  `python3 desk/deploy/flow_prefect.py --serve`
