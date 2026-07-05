# OPEN_DECISIONS — calls only the human can make

These are surfaced, not assumed. The paper build proceeds regardless; nothing real-money
moves without them. (Numbering continues from PLAN/99: O1–O6 remain open there.)

## O-F1 — Real-money venue access (supersedes/extends O6; THE strategic question)
The 2026-07-04 research pass confirms **both venues are geo-restricted for AU**:
- Kalshi: Australia on the restricted-jurisdiction list (gambling-law grounds); VPN
  circumvention risks closure + asset seizure. (Confirm clause in Member Agreement — W1.)
- Polymarket: VPN use breaches ToS §2.1.4; detection = permanent suspension + full
  forfeiture, no appeal.
Options the human must choose among (the Institute will not choose): (a) stay paper-only
and treat the Institute as an edge-research machine; (b) PM-via-VPN with a hard balance cap
(A2 worksheet will read CANNOT CERTIFY and require your signature on the unquantified
tail); (c) a lawful third-party/jurisdiction arrangement (own legal advice required);
(d) an accessible alternative venue (e.g. ForecastEx — lower depth; would need its own
fee/coverage research before any routing). **Decision needed by: end of the 4-week window
(day 28 report). Not before — paper proof does not depend on it.**

## O-F2 — Does the sports sequencing veto cover venue-wide behavioral fades?
C2 (Kalshi longshot fade) is a price-only, venue-wide behavioral strategy. Mechanically it
will fade longshots in Kalshi SPORTS markets (35,689 of 153k held markets are sports —
they dominate the daily-resolving pool that gives C2 its sample). This is not a sports
model (no team/player analytics), but it IS betting on sports outcomes. Your O1 veto was
about build sequencing of sports MODELS. **Choose: (a) fades may include sports markets
(recommended — it is the bias, not the sport, being traded, and it triples the sample
rate); (b) exclude sports from C2 (slower sample, cleaner separation).** Needed before
C2's forward seed starts (~day 10).

## O-F3 — A2 parameters at go-live
Venue balance caps (design default `min(30% bankroll, $500)` per venue) and the p_detect
basis you are willing to sign. Needed only at go-live (after O-F1).

## O-F4 — Micro-tier economics floor
GO_LIVE_TRIGGER §3 sets "projected 90-day net profit ≥ $50" as the worth-doing floor
[ASSUMPTION]. Confirm or re-set. Needed at first go-live worksheet.

## O-F5 — LLM spend for S1 — RESOLVED 2026-07-06 (user + research)
User directed free providers. Opus research pass (cited in CHANGELOG) selected **Groq
free tier** (llama-3.3-70b-versatile, 1,000 req/day, no production-use prohibition)
as primary, OpenRouter fallback; **NVIDIA NIM rejected — its Trial ToS bars production
use**. S1 standing cost: **$0**. Remaining human step: create a free account at
console.groq.com, generate an API key, set it as the GROQ_API_KEY environment variable
on this PC. S1 starts capturing forecasts on the next 16:30 run after the key exists.

## Carried open from PLAN/99 (unchanged, still yours)
- O1 sports model sequencing; O3 premium-data budget at launch; O4 real-money activation
  co-sign (hard gate, per-cell); O5 self-modification leash tier boundaries.
