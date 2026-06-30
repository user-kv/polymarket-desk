# 07 — The Moat

**Status:** PLANNING ONLY. No build authorized.
**Scope:** How the Institute builds a genuinely hard-to-replicate edge across all four moat dimensions, and an honest assessment of what a copyist would do and why they'd fail.

---

## Framing

"Moat" is the wrong word for most trading strategies — genuine alpha is leaked by success (other people see what you're doing), eroded by competition (they pile in), or decay-clocked (the market corrects the inefficiency). The Institute's four moat dimensions are chosen precisely because they resist these three failure modes. A competitor who copies the method cannot copy the execution, and a competitor who copies the execution cannot back-fill what the execution has already built.

The moat is not an argument for complacency. It is a forcing function for a specific style of construction: one that compounds privately, improves autonomously, and widens as it ages.

---

## Dimension 1: Compounding Data & Track Record

### What it is

Every forecast the Institute makes is **frozen at decision time** — prior probabilities, model inputs, and the resulting probability estimate are all locked the moment the bet is proposed, before the outcome is known. This is the **point-in-time honesty law** (Charter §Non-negotiable principles).

The result: a growing ledger of (frozen_prior, model_inputs_at_t, actual_outcome) tuples. Over months, this becomes a calibration dataset no competitor can reconstruct. They cannot back-fill it because:
1. Market prices at time t are observable in retrospect, but **the Institute's internal model estimate** at time t is not. It is private.
2. The ensemble weights, bias corrections, and calibration state at each decision point are timestamped and stored only by the Institute.
3. Even if a competitor starts the same process today, they are permanently n-bets behind in sample size, and their early bets will have been placed without the calibration data the Institute has already accumulated.

### How it is built

- Every scan writes a frozen JSON blob to `data/scans/YYYYMMDD_HHMMSS.json` with all inputs.
- The ledger (`bets.csv`) stores each bet's prior, model weights, and calibration state at time of entry.
- Settlement writes the actual outcome back to the same row.
- The calibration module (`calibration.py`, `prob_calibration.py`) is re-fit only on the historical frozen data — never on data that includes any forward look.

### How it compounds

- **Calibration improves**: With 200+ settled markets, Platt scaling and per-model RMSE weights converge to genuinely more accurate priors. Earlier data is more valuable than later data (it trained the later bets).
- **Anomaly detection sharpens**: With enough frozen priors, the Institute can detect drift — a model that was 5% over-confident on high-temperature days in summer — and correct it prospectively. A new entrant cannot spot this pattern because they lack the history.
- **The track record itself is evidence**: A 12-month auditable series of frozen priors and outcomes is a credential. It justifies deploying more capital, trying new verticals (Gate 4 evidence accumulates), and making stronger claims about edge. A competitor starting from zero cannot present this.

### Compounding rate

The moat widens faster than a competitor can catch up. If the Institute runs 10 settled markets/week across 3 verticals, it generates ~150 data points/quarter. A competitor starting today is 150 behind after Q1, 300 behind after Q2, and falling further because the Institute's calibration improves with each additional point.

---

## Dimension 2: Agent & Model Sophistication

### What it is

The Institute is not running a single model. It is running an ensemble of specialist agents — weather NWP models, macro indicator extractors, event-reasoning LLMs, smart-money copy-flow sensors — each tuned to a vertical, combined via learned weights, and continuously evaluated for decay.

### How it is built

The existing stack already demonstrates this: the weather vertical combines 6 NWP models (GFS, ECMWF, ICON, GEM, UKMO, AIFS) with inverse-RMSE weights fitted per-city from 7-day archives. The CPI vertical runs a 3-model ensemble. Gate 7's Welch-z decay detector fires the moment a component's edge degrades, before it costs significant capital.

The sophistication compounds in three ways:

1. **Vertical depth**: Each vertical is a specialist system with bespoke data pipelines, models, and calibration. A generalist with a single model cannot match a specialist with an ensemble. The weather system took weeks to build; a copyist must invest the same time from scratch.

2. **Agent-org routing**: The A6 Alpha Engine (LLM forecast swarm, built but gated off) routes market questions to the best available model for that question type. An election question goes to a political-context LLM; a macroeconomic question goes to a fundamentals model; a sports question goes to an ELO/statistics model. Getting the routing right requires iteration that only comes from running the system.

3. **Self-improvement loop**: When a vertical's SPRT rejects a strategy (accept_H0), the system proposes amendments — different calibration, different features, different model weights — and enters Gate 4 again. A human competitor who loses with a strategy typically abandons it; the Institute's adversarial gates distinguish "strategy wrong" from "implementation wrong" and try to salvage the former.

### Why a copyist can't catch up

Model sophistication is not a recipe — it is a fitted system. You can read the method (it's published), but the fitted weights, the decay detector's calibration on actual EV streams, the per-city model weights — these are internal states of a running system. Copying the code gives you the unfitted engine; years of operation gives you the calibrated one.

---

## Dimension 3: Breadth × Speed

### What it is

The Institute scans the entire Polymarket universe every 30 minutes. Across 4 market families (Macro, Sports, Politics, Crypto/Culture/Tech), hundreds of markets are in scope at any given time. A human analyst can monitor ~10 markets simultaneously and needs hours to form a view. The Institute can cover 500 markets and form views in minutes.

### How it is built

The autonomous cron pipeline on the GCP VM:
1. Fetches all active Polymarket markets via Gamma API.
2. Classifies each against the known verticals (sports event → sports vertical; temperature market → weather vertical; CPI release → macro vertical).
3. Routes to the appropriate specialist engine.
4. Generates a probability, compares to market price, and scores edge.
5. Proposes bets for any market clearing all seven gates.

This entire loop runs unattended. The human's time is spent reviewing proposals, signing off on tier escalations, and reading digest summaries — not manual forecasting.

### Speed advantage in practice

For news-driven markets (political events, crypto), speed matters because prices correct quickly when information arrives. The Institute's advantage here is not raw latency (it's not a HFT shop) but **consistency of coverage**: a human gets tired, skips a scan, misses a market. The autonomous system doesn't.

For slow-moving markets (weekly temperature highs, monthly CPI), speed matters less — but breadth does. A human monitoring 3 cities for weather can generate maybe 30 weather bets/year. The system monitoring 50 cities can generate 500. Statistical significance builds 17× faster.

### The compounding dynamic

More bets → faster Gate 4 graduation → earlier real-money deployment → more capital at work → more bets. The flywheel is slow at first (Gate 4 needs 4 weeks minimum) but accelerates as more verticals graduate.

---

## Dimension 4: The Integrated Machine

### What it is

The four dimensions are not independent — they feed each other. The integrated loop is:

```
Gate → Allocate → Execute → Settle → Decay → Recalibrate → Self-improve → Gate
```

Each component is designed to work with the others: the allocator reads calibration quality from the gate outputs; decay detection reads settled outcomes from the same ledger the allocator writes to; self-improvement reads the decay detector's output to propose vertical amendments.

### Why integration is the hardest moat to copy

A competitor can copy the Kelly formula. They can copy the Welch-z decay detector. They can even copy the 7-gate structure. What they cannot copy is **a system that has been running this full loop for 12 months** with real data flowing through every seam.

Specific non-copyable elements:
- **Calibration state at every layer**: The per-model RMSE weights in `calibration.json` are fitted on 7+ days of actual model outputs vs. observed highs. A new entrant starts with uniform weights and must run the system for weeks before they converge to anything useful.
- **Gate 4 evidence**: The forward lockbox ledger entries — n, ev, span_weeks, SPRT decisions — are accumulated over real time. You cannot simulate them; the SPRT's sequential nature means the sample must arrive in chronological order.
- **Decay baselines**: The early_ev distribution in the decay detector is fitted on the Institute's actual bet history. A fresh system has no baseline to compare against.
- **The self-improvement log**: Every strategy amendment, every vertical birth and death, every parameter change — these are in `99_DECISIONS_LOG.md`. The decisions look obvious in hindsight but were each contingent on prior system behavior that no one else observed.

### The self-improvement loop as a moat amplifier

The Institute proposes new verticals autonomously. When it identifies a market family with consistent crowd mispricing (longshot bias, anchoring to first-posted odds), it generates a pilot specification, enters it into Gate 1, and begins accumulating forward evidence. A human competitor doing manual analysis might spot the same pattern — but they must notice it, research it, design an approach, and test it. The Institute does this in parallel across every category it monitors.

Over 24 months, this produces a portfolio of strategies — some graduated and deployed, some accumulating, some dead — that collectively represent the Institute's map of the prediction-market universe's exploitable edges. The map has no substitute for lived experience.

---

## "How Someone Would Try to Copy This, and What Stops Them"

### The most plausible copy attempt

A well-resourced competitor could:
1. Read the architecture (if published or leaked).
2. Implement the same Kelly + cap cascade.
3. Subscribe to the same free data feeds.
4. Use the same LLM APIs.
5. Run the same 7-gate structure.

**What they get**: an unfitted, uncalibrated, unvalidated engine with zero track record. At this point they are exactly where the Institute was on Day 1.

### What stops them from catching up

**Time is irreversible.** Gate 4 requires 4 weeks minimum and n ≥ 50 settled markets. You cannot buy this time. The Institute's frozen prior ledger is compounding daily; the competitor's clock starts when they start.

**Calibration is private.** The Institute's per-city, per-model RMSE weights, per-vertical Platt calibration parameters — these are internal states fitted on private data (the Institute's own forecasts vs outcomes). The competitor's calibration will diverge because their prior forecasts will differ, even given the same models.

**The track record is the credential.** When the Institute goes live, it will have a 6–12 month auditable forward record. The competitor starting today cannot present this record until 6–12 months from now. If the Institute's record is strong, it justifies larger position sizes and more aggressive vertical expansion — compounding the lead.

**Self-improvement is path-dependent.** The Institute's dead strategies (Gate 4 rejected) are as valuable as the live ones — they carve out the territory where edges don't exist. A competitor learns the same lessons only by running their own experiments. They cannot import the Institute's negative results.

**The AU/VPN operational reality is a natural filter.** Few competitors will run a personal prediction-market fund from a geo-blocked jurisdiction with the specific operational discipline required. The barrier is not technical; it is the combination of regulatory awareness, operational care, and sustained commitment. Most competitors give up on paper.

### What does NOT stop them

- **The open-source tooling**: py-clob-client, Open-Meteo, and the LLM APIs are all accessible to anyone. The Institute has no lock on inputs.
- **Market discovery**: The same Gamma API is public. A competitor sees the same markets.
- **The conceptual framework**: Fractional Kelly, 7-gate validation, ensemble forecasting — all published. None of this is proprietary.

The moat is not secrecy. It is **accumulated time × disciplined execution × private calibration data**. A competitor who knows exactly what we're doing still cannot catch up because they don't have the fitted system we've been running.

---

## Moat Maintenance

The moat degrades if:
- Calibration stops updating (Institute stops running scans) — maintenance cost: near-zero (cron keeps running).
- A vertical's edge is discovered by the crowd (prices adjust, EV collapses to 0) — detection: Gate 7 / decay detector fires before this costs significant capital.
- A better free data source appears and a competitor adopts it — risk: low if the Institute's premium-data upgrade slots are activated before the competition. The free-to-premium path is designed into every vertical.
- The market universe itself changes (Polymarket adds new market types, existing types dry up) — risk: managed by the market universe scan and the self-improvement loop's vertical birth/death mechanism.

**The key maintenance discipline**: keep the automated cron running, keep the ledger accurate, and keep Gate 4 accumulating. The moat builds itself as long as the engine is running.

---

## Summary: The Moat Matrix

| Dimension | Core asset | How it accrues | Copyist failure mode |
|---|---|---|---|
| Data & Track Record | Frozen prior + outcome ledger | Every settled bet adds a row | Cannot back-fill; no frozen priors before their start date |
| Agent Sophistication | Fitted ensemble weights + decay baselines | More settled markets → better calibration | Starts with unfitted weights; months behind |
| Breadth × Speed | Full-universe scan + multi-vertical coverage | More verticals graduated → more bets → faster Gate 4 | Must rebuild each vertical from scratch |
| Integrated Machine | Gate→allocate→settle→decay→self-improve loop | System state compounds with runtime | Can copy the code; cannot copy the running state |
