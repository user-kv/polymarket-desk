# Fable 5 design changelog — audit trail

## Cycle 1 (2026-07-04)

### PERCEIVE findings that shaped v1
- Sampled all four history files + manifest + coverage report. Kalshi rows hold outcomes
  but NULL prices → every Kalshi edge was unbacktestable on current holdings; the
  decision-time price fetcher (fetcher v2) is therefore the single highest-leverage build.
- Polymarket: only 1,795 usable decision-time price series (from real trades) out of 262k
  resolved outcomes — PM behavioral claims must be validated, not assumed (consistent with
  J10).
- Weather is the only vertical whose backtest needs NO venue price history (Open-Meteo
  archive + external resolution) — hence anchor cell.

### v1 design decisions (Fable 5 judgment)
- Active set cut to 2 graduation candidates **(SUPERSEDED by red-team cycles 1–2: C2
  demoted cycle 1; C1's in-window graduation made conditional cycle 2)** (C1 weather, C2 Kalshi longshot fade) + 1
  pre-registered study (C3 PM behavioral validation) + 2 seeds (S1 geopolitics 0-fee news,
  S2 CPI). Everything else cut/backlogged: a shorter honest design beats a longer optimistic
  one.
- Engine ranking inverted from PLAN: Engine B (price-only behavioral) is the 4-week
  workhorse because it is the only engine whose backtest is automatically point-in-time
  honest. Engine C forward-only; Engine D confirmation + tape-capture only.
- Multiple-testing correction (BH q=0.10) promoted from advice to a Gate-4 gate (A1).
- Forfeiture priced into sizing as per-venue balance caps + expected-loss inequality (A2);
  venue added as a correlation factor (A3).
- Copy-flow tape capture on both venues starts week 1 under the 5c retrofit exception —
  the Kalshi tape cannot be back-filled later at any cost. Directional copy stays backlogged.

### Research pass 1 (Opus 4.8, cited) — three v1 assumptions corrected
1. **Kalshi is hard-blocked for Australia** (restricted list; closure + plausible seizure).
   v1's "route real money to Kalshi because no forfeiture risk" was WRONG — removed. Both
   venues now carry the forfeiture tail; A2 generalized from PM-only to per-venue caps;
   real-money venue escalated to O-F1/O6 as a human decision.
2. **FLB-fade net profitability is UNSOURCED.** Bürgi/Deng/Whelan confirm the bias (takers
   lose 32%; <10¢ loses 60%+) but document only "small positive" returns on the high-price
   side, on data ending Apr 2025 — before Kalshi introduced maker fees. C2 reframed: the
   backtest establishes or kills the edge; the literature only motivates the hypothesis.
   Derived side-specific fee math added (fader at 90¢ pays ~0.7% one-way, not 6.3%).
3. **Fee-regime timing:** both venues' 2026 fee rollouts apply only to markets deployed
   after activation → backtest harness must be fee-regime-aware per market; forward edge
   always assumes fees ON. Added as falsifier 2b + harness test requirement.
   Also confirmed: Kalshi candlesticks for settled markets are public/unauthenticated
   (fetcher v2 de-risked); PM fee table confirmed as held.

### Red-team cycle 1 (independent Opus 4.8) → v2 revisions
Findings: 2 BLOCKER, 4 HIGH, 4 MEDIUM, 4 LOW. Every one accepted; none waved away.
- **B1 (accepted, C2 demoted):** at a 93% win-rate target, n=50 forward has ~25% power vs
  the 90% breakeven; a real decision needs ~600 bets. C2 demoted from graduation candidate
  to backtest-study + forward seed; graduation moved to ≈week 10 via SPRT on net ROI with
  expected-n stated. §5 rewritten: all skewed-payoff cells use sequential net-ROI tests,
  never win-rate at n=50. **The honest 4-week deliverable is now: C1 (sole graduation
  candidate) + two decisive study verdicts + seeds — stated plainly in §0.**
- **B2 (accepted):** C2 backtest now requires a pre-registered spread haircut (1¢ = 1-tick
  half-spread floor ≈1.1% at 90¢ NO, replaced by F3 tape measurements when available),
  ceil() fee rounding at real contract counts, and fillability flagged as an untested
  ASSUMPTION. The +2% bar must clear after ALL costs.
- **H1 (accepted):** +21.9% correctly re-attributed to YES-side `yes_raw` GROSS; the
  NO-side fee argument no longer blesses it. W1 task: re-derive net at actual entry
  prices/sides from the existing ledger. NO-side evidence restated as 8/8, n=8, anecdotal.
- **H2 (accepted):** test family frozen at pre-registration (5 cells + C3's named buckets,
  one flat family), corrected ONCE at day 28 with Benjamini-Yekutieli (dependence-robust);
  no nested double-testing.
- **H3 (accepted):** W1 day-1–2 coverage probe added; all sample bars re-anchored to
  MEASURED availability before the pre-registration freeze; probe result is binding.
- **H4 (accepted):** durability language corrected everywhere: the bias is durable, the
  fader's net edge is perishable; decay windows sized for payoff skew, not fixed n=50.
- **M1:** A2 relabeled a placeholder; gate output is "CANNOT CERTIFY" while p_detect
  unknown. **M2:** C1 sample fixed as pooled n≥50 with ≥20/venue. **M3:** A4 remodeled:
  forfeiture = independent full-venue-balance event on top of worst trading day (−45%,
  +82% to recover). **M4:** each C2 backtest fold must contain ≥30 sub-10¢ loss events.
- **L1:** Kalshi-AU restriction to be confirmed in the Member Agreement text (W1 task).
  **L2:** favorite-underpricing labeled ASSUMPTION. **L3:** LLM cost arithmetic shown.
  **L4:** §0 reframed as "paper edge-proof machine; real-money deployment blocked pending
  human venue decision."

### Red-team cycle 2 (independent Opus 4.8) → v3 revisions
Findings: 1 BLOCKER, 6 HIGH, 2 MEDIUM, 2 LOW. All accepted.
- **c2-B1 (accepted — the sharpest finding of the whole loop):** C1's "SPRT n 50–150" had
  silently assumed a 13–23% effect (the disowned gross number) and understated σ by ~2× at
  mid prices, ignoring cross-city correlation. Fixed: C1's SPRT is powered off the W1 NET
  re-derivation with measured σ and a date-clustered effective-n discount; §0 now states
  plainly the window may produce ZERO graduations and that verdicts + a correctly-powered
  pipeline are the honest deliverable.
- **c2-H2:** pre-registered branch added on the re-derived net (≥+10% / +3–10% / <+3%).
- **c2-H3:** "weather needs no venue price history" corrected — archive proves forecast
  skill only; net-edge proof is ledger-based (165 mkts, own captures) + forward.
- **c2-H4:** spread now MEASURED per-market from candlestick yes_bid/yes_ask (1¢ as floor
  only); F3 tape validates rather than being the first measurement.
- **c2-H5/L10/M8/M9:** family correction switched to e-BH (SPRT LRs are e-values;
  anytime-valid); S1/S2 carry e-value 1; early boundary hits provisional + Tier-B review;
  BH/BY rationale corrected.
- **c2-H6:** the bar LADDER made explicit (paper-seed bar vs 2×-cost go-live bar) in both
  ARCHITECTURE §5 and GO_LIVE_TRIGGER §3; go-live SPRT is per-funded-venue, pooled
  graduation never funds a venue.
- **c2-H7:** day-1 minimal read-only probe script decoupled from the day-5 fetcher;
  pre-registration freeze moved to end-W1 after probe + F1 land.
- **c2-L11:** superseded marker added to the v1 changelog block.

### Red-team cycle 3 (independent Opus 4.8) → v4: CONVERGED
Verdict: **OPEN BLOCKERS: 0; CONVERGENCE: YES.** Reviewer verified all cycle-2 fixes as
substantive (independently re-derived C2's σ=0.30/n=400–800, the 0.7% fader fee, A4's
−45%→+82%, the LLM cost line) and graded every bullet of the mission §5 quality bar MET.
Remaining findings were 1 HIGH + 3 MEDIUM stale-text propagation misses + 2 LOW, all
folded in v4:
- c3-H1: §2's C1 table cell no longer advertises "n≥50 in 2–3 weeks" graduation — now
  points at the §5 branch and states expected-n may exceed the window.
- c3-M1: "no venue price history needed" → "no *fetched archive* venue price history
  needed; the 621 frozen scans ARE our captured decision-time prices."
- c3-M2: §5 C2 bar now pre-registers the per-market MEASURED half-spread (1¢ floor only).
- c3-M3: §8 "BY-corrected" → "e-BH-corrected".
- c3-L1: family = 4 non-C3 members + C3's k buckets (no double-count); k named at freeze;
  C3 buckets enter e-BH via a pre-registered p-to-e calibration.
- c3-L2: noted — W2 is the most fetch-dependent milestone; mitigated by re-registration
  to measured availability.
Marginal improvement across cycles 2→3 fell from structural (power model, family
correction) to editorial (stale text). Per the mission's stop rule (zero BLOCKERs +
quality bar met + diminishing marginal improvement), the design is declared CONVERGED at v4.

## Phase B — decision-time price fetcher (F1) built and verified (2026-07-04/05)
- **Routing per 5b:** spec by Fable 5 → build by Sonnet → adversarial verification by an
  independent Opus 4.8 pass → hardening by Fable 5. Delivered under `out/tools/`:
  `fetch_prices_v2.py` (Kalshi candlesticks live→historical fallback + PM trades
  expansion, append-only, resumable, --probe mode = the day-1 W1 probe), `pit_index.py`
  (`price_at`/`spread_at`, strictly-before-t), `test_fetch_prices_v2.py`, README.
- **Opus verification verdict: ACCEPT.** Confirmed the classic candle look-ahead leak is
  avoided (ts = end_period_ts, the moment the close is knowable, used strictly-before-t);
  idempotency/append-only genuine; probe read-only; manifest non-clobbering.
- **Verifier MEDIUM/LOW findings closed by Fable 5:** (1) missing-`end_period_ts` now
  raises instead of falling back to a possibly period-start ts (look-ahead trap defused);
  (2) unparseable close_time now skips the market as an error (retried next run) instead
  of fetching a now-anchored wrong window; (3) added tests: PM dual-dedup/idempotency
  against a pre-existing shared store, manifest non-clobbering, both hardening guards.
  Final suite: **20/20 passing offline** (verified independently by Fable 5, not taken on
  the delegate's word).
- Live network runs deliberately NOT executed (fence: no unbounded fetch without the
  operator starting it). First real run = the W1 day-1 `--probe`, then `--venue kalshi`.
