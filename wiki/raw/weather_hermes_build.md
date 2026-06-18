# HERMES AGENT → Self-Learning Polymarket Weather Bot (RAW)

Captured: 2026-06-12. THIS IS THE "claude or hermes" THREAD Kavee asked about.
SOURCE: Moonsat, Medium — "Hermes Agent + Polymarket: self-learning weather bot $100 → $5,000"
https://moonsat.medium.com/hermes-agent-polymarket-how-i-built-self-learning-weather-trading-bot-100-5-000-guide-233fd4a008f2

---

## What Hermes Agent is
- Open-source, **self-hosted AI agent framework by Nous Research** (released Feb 2026).
- Pitch: "a staff member who never sleeps, remembers everything, gets better every day."
- **Knowledge layer:** memory via MEMORY.md + USER.md, SQLite conversation history w/ full-text search.
- **Execution layer:** multi-agent profiles, parallel task decomposition, persistent machine access.
- **Output layer:** cron scheduling + delivery to Telegram/Slack/Discord/15+ platforms.
- **Self-improving:** after ~5–15 tool calls it auto-writes reusable "skills" as markdown
  (vs predecessor "OpenClaw" which needed manual skill updates).
- **You pick the underlying model: Claude or ChatGPT** (Claude recommended). ← Kavee's "claude or hermes" = use Hermes *with Claude*.

## How it trades Polymarket
- Autonomous agent on **Polygon** (chain 137), separate wallet funded with **USDC.e**.
- Integrates Polymarket's 3 contracts: **CTF Exchange, Neg Risk Exchange, Router**.
- Needs ERC20 `approve` (max uint256) + Conditional Tokens `setApprovalForAll`.
- Tx: EIP-1559, 200 gwei maxFeePerGas.

## Setup (≈5 min install)
1. Provision a VPS (author: **Hetzner**).
2. SSH in.
3. Install: `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`
4. Select AI model (Claude or ChatGPT).
5. Configure Telegram gateway (via BotFather).
6. Launch with `hermes`.

## Then give the agent 7 prompts to build the bot
1. **Clone repo:** fork AlterEgo's open-source weatherbot; Python venv w/ py-clob-client,
   python-dotenv, requests, web3.
2. **Create wallet:** generate Polygon wallet via eth_account; store private key in .env.
3. **Fund:** min **$10 USDC.e** + ~2 POL (~$1) gas.
4. **Approve contracts:** ERC20 approve (max uint256) to the 3 Polymarket contracts + CTF setApprovalForAll.
5. **Configure API:** link **Visual Crossing** weather API key in config.json.
6. **Test:** `python3 bot_v3.py scan` → validate trade ID before going live.
7. **Launch:** continuous background process, **hourly scan cycles**.

## Decision logic / config.json
- `min_ev: 0.10` → only trade ≥10% expected-value edge.
- `max_bet: $2.00` → tiny position cap for testing.
- Scan every 60 min. Data: **Visual Crossing**, 20+ cities.
- Example live output: `[LIVE] BUY Chicago D+1 | 82-83F @ $0.220 | EV +3.55 | $2.00`
- Sizing: "Expected Value + Kelly Criterion" (formula not given in article).

## Named performers cited (AS-CLAIMED — verify)
- **ColdMath**: $300 → $219K in 3 months (broader than the ~$120K weather-only figure elsewhere — RECONCILE).
- **Sharky6999**: **99.3% win-rate, $819K PnL** ← suspiciously high, likely market-making/arb or selective stat. FLAG.

## CAVEAT
Article is INSTRUCTIONAL, not empirical — no real backtest/live results from the author.
"$100 → $5,000" is a headline claim, not a proven outcome. Treat as a build recipe, not proof.

## Hermes repo facts (github.com/NousResearch/hermes-agent, MIT)
- Model-AGNOSTIC: 200+ models via OpenRouter, Nous Portal, OpenAI, HF, custom endpoints.
  **Claude works** (not specially highlighted, but supported). So "Hermes + Claude" = valid.
- Runs on a **$5 VPS** up to serverless. **Native Windows PowerShell support** (bundles
  Python 3.11, Node, ripgrep, ffmpeg, MinGit) ← matches Kavee's Windows setup.
- Install (Linux/mac/WSL2): `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
- Skills = "procedural memories" auto-created, stored in agentskills.io open standard.
- Memory: persistent user profiles (Honcho dialectic), cross-session recall, full-text search.
- Cron scheduler for unattended runs; spawns subagents; runs Python via RPC; CLI+Telegram+
  Discord+Slack+WhatsApp+Signal+Email gateway.
- Reqs: Python 3.11+, uv, Node.js.
- NOTE: repo shows NO trading examples — trading use is community-built (the weather bot is
  a user project wrapped by Hermes, not an official feature).

## NEXT
- Pull the Hermes repo README (github.com/NousResearch/hermes-agent) for real capabilities.
- Decide: Hermes(+Claude) autonomous agent vs just running AlterEgo weatherbot directly (simpler).
