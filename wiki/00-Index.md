---
name: 00-index
description: Home note for the Polymarket research vault — start here
---

# Polymarket Vault — Start Here

This `wiki/` folder is the **single home** for everything that isn't the live papertrading
bot's code/data. Open this whole `polymarket/` folder as an Obsidian vault and start from
this note — everything else is linked from here.

> The live bot itself (code, config, bets, dashboard) lives in **`../papertrader/`**, not
> here — it's a running program, not a note, so it stays separate. See
> [[papertrader-pointer]] for the one-line map between the two.

## Onboarding / context

- [[HANDOFF-PROMPT]] — the "give this to a fresh AI" context dump. Who Kavee is, the rules
  (paper-trade first, AU access via VPN, never bet money you can't lose), both strategies in
  one pass.
- [[PROJECT-README]] — the original project README: read-order for the guides, strategy
  one-liners, the validation ladder.

## Guides (polished, in reading order)

- [[guides/GUIDE3|Beginner Guide]] — start here if new. Plain English, defines every term.
  Rendered: `guides/Weather-and-Sports-Beginner-Guide.pdf` / `.html`.
- [[guides/GUIDE2|Dense Guide]] — fast/dense version once the basics click.
  Rendered: `guides/Weather-and-Sports-Value-Betting-Dense-Guide.pdf` / `.html`.
- [[guides/GUIDE|Complete Guide]] — the original long-form guide (weather + copy-trading +
  why Bitcoin is out). Not yet rendered to PDF — run `python guides/make_pdf.py` if needed.
- Regenerate any rendered guide after editing its `.md`: `python guides/make_pdf<N>.py`
  (script and source sit together in `guides/` on purpose — paths are relative).

## Strategies

- **Weather trading** — buy temperature-bucket shares when free ensemble forecasts
  (GFS/ECMWF/ICON/AIFS via Open-Meteo) imply a probability the market is pricing below.
  Full method in the guides above. **Live implementation:** [[papertrader-pointer]].
- [[copy-trading-masterclass|Copy Trading Masterclass]] — full research on following
  profitable wallets: 6 profit models, trader archetypes, vetting filters, tools (Poly
  Syncer, etc.), risk framework. Secondary strategy — not yet built as a bot.
- Sports value-betting — de-vig Pinnacle odds, compare to Polymarket price, track Closing
  Line Value. Covered in the guides; no separate deep-dive note yet (raw notes only, see
  [[raw/SPORTS_VALUE_BETTING]]).

## Raw research (unsorted, sourced)

Everything under `raw/` is the original capture from the research sprint — kept as-is,
just relocated. Start with [[raw/00_INDEX]] (running log) and [[raw/01_SYNTHESIS]]
(ranking + recommended path). Harvest scripts (`fetch_metadata.py`, `fetch_more.py`,
`fetch_strat3.py`, `fetch_transcripts.py`) live in `wiki/` next to `raw/` — they're
hardcoded to write into `raw/`, so keep them paired if you ever move things again.

| File | Covers |
|---|---|
| [[raw/STRATEGY_SURVEY]] | All candidate strategies considered + why these 2 won |
| [[raw/weather_web]], [[raw/weather_tools_repos]], [[raw/weather_hermes_build]] | Weather deep-dives |
| [[raw/SPORTS_VALUE_BETTING]] | Sports deep-dive (Pinnacle, de-vig, CLV, tools) |
| [[raw/copytrading_web]], [[raw/copytrading_wallets]] | Copy-trading research |
| [[raw/youtube_findings]] | Extracted intelligence from ~130 YouTube videos |
| [[raw/practical_blockers]] | AU access, fees, spreads, capital constraints |

## Where things stand (2026-06-16)

- **Weather** is the strategy with a real, running implementation: the papertrading bot in
  `../papertrader/` (see [[papertrader-pointer]]) — automated scan/settle/calibrate via
  Windows Task Scheduler, self-correcting forecast bias, real-money target **2026-06-30**.
- **Copy trading** is fully researched ([[copy-trading-masterclass]]) but not yet built —
  the planned design is to fork the papertrader's architecture (reuse `polymarket.py` /
  `ledger.py` / `engine.py` / `report.py`) with a wallet-tracking module replacing
  `forecasts.py`. Not started.
- **Sports value-betting** is guide-level only, no tooling built.
