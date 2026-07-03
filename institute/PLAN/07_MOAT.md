## CHANGELOG
- **2026-06-30 red-team + hardening pass** (rubric Tier 4):
  - Applied the rubric's "moat falsifiability" test to each dimension: stated explicitly what a copyist does, what stops them, and — critically — where the "moat" is actually weak or temporary.
  - Dimension 1 (Data): acknowledged that frozen prior data is only private if the Institute never publishes results. If calibration parameters converge publicly, the moat narrows.
  - Dimension 2 (Model sophistication): downgraded from "moat" to "lead time." Fitted weights are an 8-12 week head start, not a permanent barrier. LLM capabilities are rapidly commoditising. Honest about this.
  - Dimension 3 (Breadth × Speed): explicitly flagged that breadth is NOT a moat if the edge in each vertical is thin. Volume without edge compounds losses, not gains.
  - Dimension 4 (Integration): the most durable dimension — confirmed. But "path-dependent" integration is only a moat if the system keeps running and the edge remains positive.
  - Added "Moat failure modes" section: honest list of ways the moat collapses.
  - Cut the optimistic framing on VPN/AU as a "natural filter" — it is a risk, not an advantage.
  - All speculative claims tagged [ASSUMPTION].

---

# 07 — The Moat

**Status:** PLANNING ONLY. No build authorized.
**Scope:** An honest assessment of how hard (or easy) this system is to copy, and what actually defends the edge.

---

## Framing

Most trading strategies have no moat. Alpha is leaked by success, eroded by competition, or decay-clocked as the market corrects the inefficiency. The four dimensions below are chosen because they resist at least two of these failure modes. Where a dimension only resists one (or none), this document says so.

**Moat honesty law:** a weak moat disclosed and managed is better than a strong moat assumed and not defended. Every "what stops them" below includes an honest answer to "what does NOT stop them."

---

## Dimension 1: Compounding Data and Track Record

### What it is

Every forecast the Institute makes is **frozen at decision time** — prior probabilities, model inputs, and the resulting probability estimate are locked before the outcome is known. The result is a growing ledger of `(frozen_prior, model_inputs_at_t, actual_outcome)` tuples.

### What a copyist does

1. Starts the same process today.
2. Uses the same free data feeds (Open-Meteo, Gamma API).
3. Runs the same Kelly + 7-gate structure.
4. Gets the same unfitted, uncalibrated engine — the Institute had on Day 1.

### What stops them

**Time is irreversible.** Gate 4 requires n ≥ 50 settled markets and a 4-week minimum span. This cannot be purchased or simulated. The SPRT's sequential nature requires the sample to arrive in chronological order.

**Private calibration state.** The per-city, per-model RMSE weights, and Platt calibration parameters are fitted on the Institute's own forecasts vs. outcomes. A copyist using the same models will produce different forecasts — their calibration will diverge from the Institute's from the first bet.

**Track record as credential.** A 6–12 month auditable forward record justifies larger position sizes and aggressive vertical expansion. A copyist starting today cannot present this record for 6–12 months.

### Where this is actually weak

- The frozen prior data is only private as long as the Institute does not publish its forecasts. If the Institute ever publishes its probability estimates (e.g., in a leaderboard or research output), the moat in this dimension narrows significantly.
- If calibration parameters converge to the same values a competitor would derive (because both are fitting on the same underlying model outputs), the "private calibration" moat is illusory. [ASSUMPTION: divergence is expected given different forecast histories, but this has not been empirically verified.]
- The track record moat matters mainly if the Institute scales capital. For purely personal-scale trading ($200–$1,000), the credential has limited practical leverage.

**Verdict:** Strong moat for the calibration/track-record dimension IF the Institute keeps running and does not publish its internal estimates. Weak at personal capital scale where credential does not unlock more capital.

---

## Dimension 2: Agent and Model Sophistication

### What it is

The Institute runs an ensemble of specialist agents — NWP weather models, macro extractors, LLM-event reasoners, copy-flow sensors — combined via learned weights, continuously evaluated for decay.

### What a copyist does

1. Reads the method (published or reverse-engineered from the open-source stack).
2. Uses the same LLM APIs (GPT-4o, Gemini Flash — both commercially available).
3. Uses the same NWP data (Open-Meteo is free).
4. Implements the same ensemble weighting (inverse-RMSE is a published method).

### What stops them

**Fitted weights take time.** The per-city, per-model RMSE weights require 7+ days of actual model output vs. observed data to converge. A new entrant starts with uniform weights and produces noisier forecasts for their first several weeks.

**Decay detector has no baseline.** `decay.py`'s Welch-z test requires an `early_ev` distribution fitted on actual bet history. A fresh system has no baseline. It cannot distinguish edge erosion from startup variance for the first min_window × 2 = 16 bets per cell.

**Routing takes iteration.** The A6 Alpha Engine's question-routing (which LLM for which market type) requires empirical feedback to tune. Initial routing guesses will be wrong in ways that only become visible after running forward.

### Where this is actually weak [HONEST ASSESSMENT]

**Model sophistication is an 8-12 week lead, not a permanent barrier.**

- LLM capabilities are commoditising rapidly. A copyist who starts today has access to the same or better base models.
- RMSE weight fitting converges in 1-2 weeks of operation. After that, the weights are similar for anyone running the same NWP models.
- The ensemble weighting method (inverse-RMSE) is published in the weather forecasting literature. The Institute has no IP lock on it.
- If the Institute's edge comes primarily from the ensemble method rather than from unique data or private calibration, this moat dissolves over 2–4 weeks for a competent copyist.

**Verdict:** Weak moat for model sophistication alone. It is a meaningful head start (8–12 weeks) but not a durable barrier. Do not plan around it persisting beyond 6 months in any single vertical.

---

## Dimension 3: Breadth × Speed

### What it is

The Institute scans the full Polymarket universe every 30 minutes, across 4+ market families, forming views on hundreds of markets where a human can monitor ~10.

### What a copyist does

1. Deploys the same autonomous cron pipeline (the architecture is not secret).
2. Subscribes to the same Gamma API.
3. Covers the same markets.

### What stops them

**Consistency of coverage.** A human gets tired, skips scans, misses markets. The automated system doesn't. This is a meaningful operational advantage over manual competitors.

**Gate 4 in parallel.** Running many markets simultaneously means more cells accumulate Gate 4 evidence concurrently. A copyist must build all their verticals from scratch and wait the same Gate 4 minimum span for each.

### Where this is actually weak [CRITICAL CAVEAT]

**Breadth without edge is worse than no breadth.**

If a vertical has no genuine edge, scanning it continuously and placing bets does not compound — it compounds losses. The 7-gate structure is supposed to prevent this, but:
- A vertical that passes Gate 4 at n=50 with marginal significance (p just under 0.05) has a ~5% false positive rate by design.
- With 23 verticals, multiple-comparisons math implies roughly 1 false-positive graduate on average. That cell then places real-money bets with no actual edge.
- Speed × breadth means a false-positive cell damages the book faster than a slow human trader would.

**Mitigation:** Run Bonferroni or Benjamini-Hochberg correction across verticals. The rubric requires multiple-comparisons correction (Tier 1.3). Ensure Gate 4 significance threshold is adjusted for the number of vertical candidates being tested simultaneously.

**Verdict:** Breadth is a real operational advantage over human competitors. It is not a moat against another automated system. The real question is whether edge-detection gates are tight enough to prevent breadth from amplifying false-positive cells.

---

## Dimension 4: The Integrated Machine

### What it is

The four dimensions feed each other in a closed loop:

```
Gate → Allocate → Execute → Settle → Decay → Recalibrate → Self-improve → Gate
```

Each component is designed to work with the others: allocator reads calibration quality from gate outputs; decay detection reads settled outcomes from the same ledger; self-improvement reads decay outputs to propose amendments.

### What stops a copyist

**A copyist can copy the code. They cannot copy the running state.**

Specific non-copyable elements:
- **Calibration state at every layer:** Per-model RMSE weights, per-vertical Platt parameters — private states fitted on private data.
- **Gate 4 evidence:** Forward lockbox entries accumulated over real time in chronological order. Cannot be simulated.
- **Decay baselines:** `early_ev` distribution requires actual bet history to exist. A fresh system has no baseline for min_window × 2 bets per cell.
- **Decisions log:** Every strategy amendment, vertical birth/death, parameter change — `99_DECISIONS_LOG.md` represents path-dependent knowledge that a copyist must re-derive through their own experiments. The negative results (Gate 4 rejects) are as valuable as the live strategies.

### Where this is actually weak

**Integration moat only holds while the system keeps running and the edge stays positive.**

If the Institute stops running scans for 30+ days, the calibration data goes stale, the track record stops compounding, and decay detection loses its baseline recency. The moat is maintenance-dependent. Maintenance cost is near-zero (cron keeps running) but not zero.

**If the edge in a key vertical disappears** (market corrects the inefficiency), the integration moat in that vertical evaporates regardless of how long the system has been running. Gate 7 detects this, but only after meaningful capital has been risked in the decay phase.

**Verdict:** The most durable moat dimension. Path-dependent integration is genuinely hard to replicate without running the system for an equivalent period. The vulnerability is systemic edge decay — which is why Gate 7 and the self-improvement loop matter more than any single technical component.

---

## Moat Failure Modes (The Honest List)

The moat fails if any of the following occur:

1. **No genuine edge exists in the graduated verticals.** The 7-gate structure is designed to catch this, but multiple-comparisons failures are possible. A false-positive cell that scales ruins the track record and may deplete the bankroll before decay detection fires.

2. **Calibration stops updating.** Cron stops running, or the ledger becomes stale. Decay baselines lose relevance. Calibration weights drift. This is the cheapest failure mode and the easiest to prevent.

3. **Crowd adaptation in a key vertical.** If the Institute's weather forecast edge (favorite-longshot bias in high-temperature markets) becomes well-known and targeted by other bettors, prices correct and EV collapses. Gate 7 will detect this but only after some capital is lost.

4. **A better data source appears and a competitor adopts it first.** Open-Meteo is a free baseline. If ECMWF releases a higher-resolution free product, the NWP ensemble advantage in the weather vertical narrows. Risk: low if the Institute's premium-data upgrade slots (built into the vertical design) are activated before the competition. [ASSUMPTION]

5. **Venue forfeiture.** VPN detection by Polymarket suspends the account and zeroes the balance. This terminates the operation regardless of edge quality. Not a moat failure — but it ends the system before the moat compounds. The most operationally critical risk at the user's scale. See `06_EXECUTION_VENUE.md`.

6. **Building breadth at the expense of depth.** Self-improvement proposes new verticals faster than existing ones can be properly validated. Over-extension leads to false-positive graduates and capital distributed across under-validated cells.

---

## Summary: The Moat Matrix (Honest Version)

| Dimension | Core asset | How it accrues | Copyist failure mode | How strong / how durable |
|---|---|---|---|---|
| Data & Track Record | Frozen prior + outcome ledger | Every settled bet adds a row | Cannot back-fill frozen priors | Strong IF not published; limited leverage at personal capital scale |
| Agent Sophistication | Fitted ensemble weights + decay baselines | More settled markets → better calibration | Starts with uniform weights; 8–12 week lag | Weak as permanent moat; meaningful head start only |
| Breadth × Speed | Full-universe scan + multi-vertical coverage | More verticals graduated → more bets → faster Gate 4 | Must rebuild each vertical from scratch | Real vs human competitors; not vs another automated system; requires tight gate discipline |
| Integrated Machine | Gate→allocate→settle→decay→self-improve loop | System state compounds with runtime | Cannot copy running state | Most durable; only holds while system keeps running and edge persists |

**Bottom line:** The Institute's moat is real but not impregnable. Its durability depends on (a) genuine edge in graduated verticals (Gate 4 discipline), (b) the system continuing to run (maintenance), and (c) not being terminated by venue forfeiture before the track record compounds. None of these are guaranteed. The moat earns the right to operate at increasing scale only if the evidence supports it.
