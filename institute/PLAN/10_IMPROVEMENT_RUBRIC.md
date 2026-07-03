# What "Better" Means — the Improvement Rubric

**Purpose:** the standard against which every plan document is red-teamed and hardened.
Written before the improvement pass so the goalposts cannot move. Opus-owned.

## The definition
The plan is **better** when, executed, it produces **higher risk-adjusted REALIZED (not
backtested) edge per unit of capital and build-effort, while being more honest with itself —
failing fast and cheap where it is wrong.** Funds die of self-deception (overfit backtests,
ignored costs, edges that vanish on contact, ruin from hidden correlation), not of a shortage
of clever ideas. So the rubric weights survival and falsifiability ABOVE sophistication.

**Cross-cutting law:** better usually means SHARPER, MORE HONEST, and often SHORTER. Cutting a
fake edge improves the plan more than adding a speculative one. Reject any change that only
adds length, ambition, or optimism without adding rigor.

## Tier 1 — Survival & self-honesty (highest leverage; these are what kill funds)
1. **Cost-adjusted edge.** Every edge restated NET of taker fee (0% geopolitics .. 1.8%
   crypto), spread, slippage, and partial-fill risk. An edge that does not clearly survive
   costs is CUT or demoted. Flag every place a gross 2-5% "edge" is really thin net.
2. **Falsifiability & fast kill.** Every vertical/engine gets a PRE-REGISTERED success metric,
   required sample size, and kill threshold — decided before data, never moved. Always the
   cheapest possible disproof first. "How would we know this is wrong, and how fast/cheap?"
3. **Overfit & multiple-testing defense.** We scan 23 verticals x many params -> the more we
   test, the higher the bar. Require walk-forward OOS, point-in-time frozen priors, and an
   explicit multiple-comparisons correction / trial-count deflation. No in-sample claims.
4. **Edge durability under adaptation.** Assume the crowd and rival bots adapt. Classify each
   edge: STRUCTURAL/behavioral (durable, e.g. favorite-longshot) vs INFORMATIONAL (decays as
   copied). Weight durable edges; treat informational edges as perishable with a half-life.

## Tier 2 — Risk of ruin
5. **Correlation honesty.** Macro cells (CPI/Fed/jobs/GDP) CO-MOVE; "diversified" caps are
   illusory if the factor model misses it. Verify the cap cascade survives a correlated
   drawdown; stress a day where every macro cell loses together.
6. **Tail / oracle / venue risk priced in.** UMA dispute & ambiguous-resolution risk, venue
   insolvency, and AU/VPN ToS-forfeiture are real loss channels — sized, not hand-waved.
7. **Ruin math at small capital.** Confirm quarter-Kelly across CORRELATED cells survives a
   realistic losing streak without crippling the bankroll. If not, cut the fraction.

## Tier 3 — Edge maximization (only after Tiers 1-2)
8. **Genuine ensemble independence** (the CPI 3rd-model lesson generalized) and best-in-class
   methods per engine, but only where they beat the cheap baseline net of cost/effort.
9. **Build-effort ROI.** Re-rank the roadmap by edge-density PER unit of build effort, not raw
   edge. Prefer cheap, durable, high-volume wins early (fast, honest track record).

## Tier 4 — Defensibility & adaptivity
10. **Compounding moat** that a copyist cannot fast-forward; **meta-learning that does not
    overfit noise**; decay detection that retires dead strategies without churning on variance.

## Tier 5 — Coherence & craft (necessary, not sufficient)
11. **Resolve cross-doc contradictions** (e.g. sports veto vs Tier-1 ranking; fee-vs-edge).
12. **Unambiguous build interfaces** — a builder should never have to guess. Explicit
    dependencies, inputs/outputs, and data contracts. Reduce build risk.
13. **Cut bloat; source or flag every claim.** Every number is sourced, derived, or labeled
    ASSUMPTION. Speculation is marked as such.

## How to apply (for each document)
- RED-TEAM FIRST: attack the doc's claims adversarially (where is it fooling itself? what
  breaks it? what costs/risks are omitted?). THEN rewrite to survive the attack.
- Prepend a short `## CHANGELOG` listing the material changes and WHY (auditable).
- Keep it sharp. A shorter, more honest doc beats a longer, more optimistic one.
- Surface any cross-document inconsistency for the synthesis pass (roadmap/decisions/charter).

## Definition of done
A document is "better" when: every edge is net-of-cost, every claim is falsifiable with a
pre-set kill criterion, overfit/correlation/tail risks are explicit, contradictions are
resolved, and nothing was added that doesn't increase rigor.
