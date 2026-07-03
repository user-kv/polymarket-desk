# Context & Memory Architecture — how the bot uses everything without burning tokens

## Plan Document 11 · PLANNING ONLY · answers "how does one AI use all this without token blowup?"

## The reframe that dissolves the problem
"All this information" is TWO different corpora that must never be confused:
- **Build-time reference** (the PLAN/, research, specs): read by HUMANS and BUILDERS. It is
  NEVER in the live trading loop. It shapes the code; it is not consumed at runtime.
- **Runtime state** (market data, frozen priors, calibration numbers, ledgers, lessons):
  what the live bot actually touches per decision. This is tiny and BOUNDED by design.

The bot never loads the 4000-line plan (or the whole history) into a context. That would be
the amateur move. It loads only what a single decision needs.

## Why the token budget is naturally small (the load-bearing insight)
1. **95% of the work is NUMERICAL, not LLM.** The weather/CPI/quant ensembles read structured
   numbers (calibration weights, price history, RMSE tables) and do arithmetic. Zero LLM
   tokens. The accumulated frozen-prior history lives in JSONL/SQLite and feeds MODELS as
   numbers — it is never pasted into a prompt. Ten years of history costs ~0 tokens to "use"
   because a model reads it as a vector, not as prose.
2. **LLM use is SURGICAL and per-market.** Only the news/reasoning engine (Engine 3) uses an
   LLM, and each agent sees ONE market + a handful of retrieved evidence snippets (~few K
   tokens), hard-capped. Per the hardened cost model: ~$0.63 base / ~$3 worst-case per
   50-market pass. No agent ever sees the whole corpus.
3. **State is externalized.** calibration.json, bets ledger, the market stores, the lessons
   log — all on disk/DB. The loop reads the FEW relevant rows per task and discards them.

So the design principle is: **externalize state, compute numerically, retrieve surgically.**

## The tiered memory (where RAG / GraphRAG actually fit)
| Tier | Content | Access method | LLM tokens |
|------|---------|---------------|-----------|
| 0 | Structured numeric state (calibration, priors, ledgers) | direct DB/file read into models | ~0 |
| 1 | Per-task context (one market + its model + fresh evidence) | assembled per decision, hard-capped | low, bounded |
| 2 | News + lessons corpus | **vector / BM25 retrieval (top-k), contextual retrieval** | only the k chunks |
| 3 | Whole-corpus meta questions (cross-vertical patterns, provenance) | **GraphRAG / knowledge graph, run PERIODICALLY** | batched, offline |

- **Tier 2 (per-market evidence + lessons): vanilla vector/BM25 retrieval.** Anthropic's
  Contextual Retrieval (contextual-prefix + BM25 + cosine rerank) cuts retrieval-failure
  35-67%. This is the right tool for "pull the 5 relevant news snippets / past lessons for
  THIS market." The `claude-obsidian:wiki-retrieve` tooling already implements exactly this.
- **Tier 3 (meta-learning + navigation): GraphRAG — YES, but only here.** GraphRAG builds a
  knowledge graph + community summaries and excels at GLOBAL synthesis over a large corpus
  ("which edges decayed after being copied?", "what connects our losing macro bets?", "what
  do we know about FDA verticals?"). That is precisely the META-LEARNING brain (doc 08) and
  human/agent navigation of the research — run it on a schedule (nightly/weekly), NOT per
  trade. Per-market forecasting must NOT call GraphRAG (too slow, overkill, unnecessary).
  The `graphify` skill builds this (god nodes, community detection, query/path/explain) — we
  point it at the accumulated lessons + PLAN corpus for the meta-layer.

## Concrete runtime budget (a single forecast)
market row (~0.5KB) + vertical model state (~2KB numeric) + [Engine 3 only] top-5 evidence
chunks (~3KB) -> a few thousand tokens, capped. The ensemble math adds zero. A 50-market
cadence pass stays well under the circuit-breaker in doc 04.

## Why this is also a MOAT (ties to doc 07)
An efficient tiered memory that RETRIEVES over years of frozen priors + distilled lessons
compounds: the meta-brain gets smarter as the corpus grows, while per-decision cost stays
FLAT. A copyist starting today has an empty Tier 0/2/3 and cannot back-fill it. Cheap-to-run
+ compounding-knowledge is the combination competitors can't fast-forward.

## Decisions
- **D-CTX-1:** the PLAN is build-time only; never loaded at runtime.
- **D-CTX-2:** numeric state feeds models directly (Tier 0); no prose prompts for history.
- **D-CTX-3:** Tier-2 retrieval = contextual vector/BM25 (reuse wiki-retrieve pattern), top-k,
  hard-capped, per-market.
- **D-CTX-4:** GraphRAG (graphify) is the PERIODIC meta-learning + navigation layer only —
  never on the per-trade hot path.
- **D-CTX-5:** every LLM call has a token cap; the cadence pass has a hard cost circuit
  breaker (doc 04).
