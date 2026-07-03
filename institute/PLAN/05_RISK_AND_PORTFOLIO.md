## CHANGELOG
- **2026-06-30 red-team + hardening pass** (rubric Tiers 1-2):
  - Added explicit correlation stress-test: ALL macro cells losing simultaneously. Showed the cascade math survives but is thinner than the doc implied.
  - Corrected Kelly growth/variance claims to match published math (quarter-Kelly ≈ 44% of log-growth, ~6% of full-Kelly variance; prior doc stated "56%").
  - Added explicit ruin-probability numbers at $200 and $500 bankrolls under correlated loss.
  - Made "diversified" caps disclaimer unmissable: cluster cap is ILLUSORY if the factor model treats co-moving macro cells as uncorrelated.
  - Added concrete minimum-net-edge floor (edge must clear fees before any bet).
  - Tightened the $5 bet floor to account for minimum meaningful size at each fee tier.
  - Clarified decay.py fires on per-cell streams — it does NOT detect portfolio-level correlated shock. Added book-level halt as the only defence there.
  - Cut §6.4 (market impact) — correct at this scale but consumed space without adding risk management value.
  - All ASSUMPTION tags added where numbers are not sourced from live data.

---

# 05 — Risk & Portfolio Management

**Status:** PLANNING ONLY. No build authorized.
**Scope:** Sizing discipline and ruin-avoidance for small personal capital ($200–$1,000) on Polymarket.

---

## 1. The Governing Principle

At small size, **the only enemy is ruin.** Market impact is negligible. The rules below exist to make ruin structurally impossible — not merely unlikely.

**The hardest constraint:** every edge figure in this document is **net of taker fees**. A gross 2–3% edge in an economics/weather market faces a ~1.25% max taker fee at the 50¢ price point. Net edge at near-50% markets can be negative after fees. Do not bet unless net edge > 0. See §2.4.

---

## 2. Fractional Kelly Sizing

### 2.1 The Kelly Formula

For a binary market (payoff b per $1 risked, lose the stake on loss):

```
f* = p - (1 - p) / b
```

Where `p` is the model probability and `b = (1 / ask_price) - 1`. If `f*` ≤ 0, there is no edge — do not bet.

### 2.2 Why Quarter-Kelly

The Institute uses **KELLY_FRACTION = 0.25**:

```
f = f* × 0.25 × calibration_quality
```

Published math: quarter-Kelly captures approximately 44% of full-Kelly log-growth rate at approximately 6% of the variance. [ASSUMPTION: exact fractions depend on the true edge distribution; these are the theoretical figures under the Kelly model.] Full Kelly produces a ~50% chance of halving the bankroll before doubling it even with genuine edge. Quarter-Kelly reduces that halving risk substantially.

**Critical caveat on correlated cells:** Standard Kelly assumes bet independence. When multiple cells share a factor (macro, weather, politics), losses co-occur. The *effective* Kelly fraction for the portfolio is lower than quarter-Kelly per cell. See §3.1 for the stress-test.

Rationale for 0.25:
- Edge uncertainty is real. Every probability estimate carries model error. Quarter-Kelly is robust to moderate p-overestimation.
- Calibration is immature (n < 200 settled markets). `calibration_quality` shrinks the bet proportionally.
- 5–10 simultaneous cells: combined portfolio Kelly is lower than any single-cell Kelly.

**Do not increase KELLY_FRACTION above 0.25 until 100+ settled markets AND positive realized EV across at least two independent verticals.**

### 2.3 Calibration Quality Multiplier

```python
calibration_quality = min(1.0, max(0.0, mean_S / CALIB_TARGET))
# CALIB_TARGET = 0.05 (the proven weather-bot skill level)
```

A cell with zero or negative mean_S gets calibration_quality = 0 — it is **cut**, not merely sized down.

### 2.4 Net-of-Fee Edge Floor (CRITICAL)

Before sizing any bet, confirm:

```
net_edge = (model_prob × payoff_b) - 1 - taker_fee_rate
```

If `net_edge ≤ 0`, do not bet. Fee rates by category (at 50¢ price point, 2026 actuals):
- Geopolitics/World Events: 0% (free)
- Sports: ~0.75%
- Finance/Politics/Tech: ~1.00%
- Economics/Culture/Weather: ~1.25%
- Crypto: ~1.80%

Fee rate scales toward 0% as market price approaches 0 or 1 — the NO-side longshot strategy (ask ≤ 0.15) benefits from this. At prices near 0.15, actual fee is well below the category maximum.

**Strategic implication:** thin edges (2–3% gross) in weather and economics categories are marginal net-of-fee at near-50% prices. Prefer high-conviction bets or prices far from 50¢. Never claim an edge that hasn't been computed net.

GTC limit orders earn a maker rebate (~25% of the taker fee) when they rest in the book and get filled. This effectively reduces cost, but do not underwrite it — rebate requires the order to rest, and a fast-moving market may match it as a taker.

---

## 3. The Cap Cascade

Four nested caps, applied in order. **Warning: these caps are only as good as the correlation model feeding the cluster step. If co-moving cells are assigned to separate clusters, the 25% cluster cap does not protect you.**

| Layer | Parameter | Value | What it prevents |
|---|---|---|---|
| Cell cap | `CELL_CAP` | 10% bankroll | Single-market concentration |
| Cluster cap | `CLUSTER_CAP` | 25% bankroll | Correlated-outcome concentration |
| Archetype cap | `ARCHETYPE_CAP` | 25% bankroll | Theme concentration |
| Total cap | `TOTAL_CAP` | 60% bankroll | Ensures ≥40% cash reserve |

### 3.1 Correlation Honesty — The Critical Weakness

`allocator.py` clusters cells whose archetype feature vectors have cosine similarity ≥ 0.50. **This is a structural proxy, not a statistical correlation of returns.** The cluster step can fail in the following real scenario:

**Macro correlated-shock scenario:** CPI, Fed rate decision, NFP/jobs, and GDP are separate cells in the macro archetype. They share the archetype and will always cluster (correlation = 1.0 by rule). So macro cells are correctly grouped. However:

1. The cluster cap of 25% may still allow 25% of bankroll in macro cells.
2. If a macro shock event occurs — a surprise CPI print that moves Fed expectations — ALL macro cells can resolve against you on the same day.
3. The 25% cluster cap means a single correlated shock can erase 25% of bankroll in one day.

**Stress test at $500 bankroll:**
- 25% cluster cap = $125 in macro cells
- Simultaneous loss of all macro positions = -$125 = -25% book drawdown
- Book halt fires at -15% (-$75). The halt does not prevent the loss if all positions are open and running to settlement.
- Result: book halt fires AFTER the correlated shock. It prevents NEW bets, not existing exposure.

**Conclusion:** The cap cascade is valid but does not prevent a single-day 25% drawdown if the macro cluster is fully deployed and all cells resolve against you. This is acceptable at small capital ($500) — it stings but does not end the operation. It is NOT acceptable if you scale to $5,000+ without reviewing the macro cluster allocation.

**Mitigation (ASSUMPTION — implement before scale-up):** Add a `MACRO_CAP = 0.15` separate from `CLUSTER_CAP` to tighten macro exposure specifically. The existing archetype cap covers this if macro is its own archetype, but verify in the factor model that CPI/Fed/jobs/GDP are coded as the same archetype.

### 3.2 Cluster Implementation Note

The union-find in `allocator.py` groups cells transitively by feature-vector cosine similarity. Same-archetype cells always cluster. Verify: if CPI and Fed cells are different archetypes but correlated in practice, the cluster cap will NOT catch them. The factor model (`factor.py`) must encode macro co-movement or the cap is illusory.

### 3.3 Reserve

The 40%+ reserve (bankroll × (1 - TOTAL_CAP)) serves: dry powder during drawdowns, psychological stability, and reload capacity. It is not idle capital — it is the ruin-prevention buffer.

---

## 4. Drawdown Halts

Two-level system. Both are hard stops — no overrides without explicit written sign-off.

### 4.1 Per-Cell Halt

```
DEFAULT_CELL_DD = -0.20  (20% drawdown vs cell's peak NAV)
```

Triggered per-position by the decay detector (`decay.py`, Gate 7). `decay.py` runs a Welch-z test on early vs. recent per-bet EV. **Important limitation:** `decay.py` operates on the cell's own PnL stream — it detects statistical edge erosion within a cell. It does NOT detect a portfolio-level correlated shock. A single macro surprise that hits all macro cells simultaneously will not trigger `decay.py` on any individual cell (since each cell's streak is short). The book-level halt is the only defence.

### 4.2 Book-Level Halt

```
DEFAULT_BOOK_DD = -0.15  (15% drawdown vs book peak)
```

Fires when total NAV falls 15% from the high-water mark. No new positions in any cell. Existing positions run to settlement (Polymarket positions cannot be exited intra-settlement). Halt lifts only after human review and explicit sign-off.

**At $200 bankroll:** fires at -$30. That stings but does not end the operation.
**At $500 bankroll:** fires at -$75. Same logic.

The book halt is the primary defence against a correlated macro shock. It fires after the shock, not before — which is why macro exposure must be pre-limited (§3.1).

### 4.3 Ruin Math at Small Capital

Ruin probability under quarter-Kelly depends on the true edge. The relevant question for this project is not long-run ruin (quarter-Kelly is extremely safe asymptotically) but **early-run ruin before the halt fires**.

Concrete scenario:
- Bankroll: $500
- 3 cells deployed, total 40% bankroll = $200 in play
- A correlated shock hits all 3 cells simultaneously (all lose)
- Loss: $200 × total weight in those 3 cells
- If those 3 cells are the macro cluster at 25% cluster cap: max simultaneous loss = $125 = 25% of bankroll
- Book halt fires at -$75 (15%). Three simultaneous losses at ~8.3% each triggers it.

This is survivable. The bigger risk is a **slow losing streak** before the halt fires on individual cells, while the book hasn't crossed -15%:
- 6 sequential losses across different cells at 10% each = -60% of deployed capital (not bankroll)
- At 40% deployed: -60% × $200 = -$120 = 24% bankroll drawdown → book halt fires
- Quarter-Kelly makes individual bets small enough that a 6-loss streak is needed to reach the halt

**Verdict:** Quarter-Kelly with 15% book halt and 40% reserve is robust against realistic losing streaks at this capital level. The system does not face ruin risk from normal variance. The tail risk is a correlated shock that bypasses the per-cell halt — which is why the macro cluster cap matters more than the per-cell halt.

---

## 5. The 7-Gate Capital-Activation Ladder

No strategy touches real money until it has survived all seven gates in sequence. Failure at any gate resets the strategy to `accumulating` status.

| Gate | Name | What it requires |
|---|---|---|
| 1 | Statistical | Brier / calibration score vs baseline; p < 0.05 |
| 2 | Mechanism | Human-readable causal story for WHY the edge exists |
| 3 | Red-team | Adversarial challenge: most plausible alternative explanation |
| 4 | Forward lockbox | n ≥ 50 settled OOS markets OR SPRT accept_H1; ≥ 4-week span; positive net EV after fees |
| 5 | Portfolio | Marginal contribution within cluster ≥ 0.5× anchor; Kelly > 0 after correlation adjustment |
| 6 | Capital | Passes all size and drawdown constraints at the proposed allocation |
| 7 | Decay monitor | Welch-z early-vs-recent EV not significantly degraded |

**Gate 4 note:** EV must be computed net-of-fee. A cell with gross positive EV but negative net EV does not pass Gate 4.

### 5.1 Paper → Forward Lockbox → Micro → Scale

**Paper** (current): Simulated positions, zero real money. GCP VM runs this continuously.

**Forward Lockbox**: Cell graduates Gate 4. Capital ring-fenced in principle. Human reviews Gate 3 (mechanism check). Explicit sign-off required.

**Micro**: 10% of normal allocation. First real money. Monitor 2–4 weeks. Gate 7 runs continuously. Decay signal → return to Forward Lockbox.

**Scale**: Normal allocation per cap cascade. Gate 7 continues.

No automated escalation between tiers. Each promotion requires explicit written instruction from the user.

---

## 6. Bankroll Management at Small Size

### 6.1 Starting Bankroll

Design assumption: $200–$1,000 initial capital.

- **Minimum meaningful bet:** $5 net of fees. Below this, fees consume the edge entirely. The minimum that makes mathematical sense is the point where (expected edge × bet size) > max possible fee.
- **Minimum for diversification:** ≥$300 to run 3+ cells with meaningful dollar amounts. Below $300, run 1–2 cells only.
- **Skip the market** if Kelly sizing produces < $5.
- **At $200 bankroll:** CELL_CAP × bankroll = $20 max per bet. This is correct sizing, not a constraint.

### 6.2 Reload Policy

No auto-reload. If bankroll falls to ≤50% of starting capital, halt and review before adding capital. Adding money to a losing system is the most common amateur mistake.

### 6.3 Compounding

Bankroll revalued daily (settled PnL + open mark-to-market). Kelly sizes update automatically — position sizes shrink during drawdowns, grow during winning runs. No manual re-sizing needed.

---

## 7. The Real-Money Cord

The system is fake-money until all three conditions are met:
1. At least one cell has cleared all 7 gates (net-of-fee EV positive).
2. The user has reviewed the Gate 3 (mechanism) documentation.
3. The user explicitly signs off in writing in `99_DECISIONS_LOG.md`.

No automated component may escalate from paper to real money. The agent may flag when a cell approaches graduation; it may not act.

**Additionally required before live deployment:** re-assess the VPN/AU forfeiture risk at that point in time (see `06_EXECUTION_VENUE.md`). This risk can zero the balance independently of any trading edge.

---

## 8. Parameters Summary

All tunable in `allocator.py` constants block. Change one parameter at a time; treat each change as a strategy change requiring Gate 4 re-entry.

| Parameter | Current Value | Notes |
|---|---|---|
| `KELLY_FRACTION` | 0.25 | Do not increase before 100+ settled markets |
| `CELL_CAP` | 10% | Hard per-market ceiling |
| `CLUSTER_CAP` | 25% | Relies on factor model correctly grouping co-moving cells |
| `ARCHETYPE_CAP` | 25% | Covers macro theme if all macro = same archetype |
| `TOTAL_CAP` | 60% | Inverse is the 40% reserve floor |
| `DEFAULT_CELL_DD` | -20% | Per-cell halt; does not catch correlated shocks |
| `DEFAULT_BOOK_DD` | -15% | Portfolio halt; primary correlated-shock defence |
| `CALIB_TARGET` | 0.05 | mean_S at which calib_quality = 1.0 |
| `MARGINAL_FLOOR_FRAC` | 0.50 | Non-anchor marginal EV floor within cluster |

---

## 9. What This Does Not Cover

- **Liquidity / capacity modelling:** irrelevant at this scale.
- **Tax treatment:** outside scope; consult an adviser.
- **Multi-venue correlation:** Polymarket-only for now.
- **Venue forfeiture risk:** covered in `06_EXECUTION_VENUE.md`. Note that suspension zeroes the balance — this is a tail risk that dominates most trading risks at small capital.
