# AI Hedge Fund — LangGraph Multi-Agent System
## Plan based on FINCON, Benchmarking, and D3 papers

---

## Context

The user wants to build a finance-focused multi-agent AI system using LangGraph. The system should analyze stocks, debate investment theses, manage risk, and learn from its own decisions over time. Everything must run on free/open-source APIs and LLMs. This plan synthesizes the three research papers into a concrete build plan.

---

## What the Papers Actually Teach Us

### FINCON → Hierarchy + Memory + Verbal Reinforcement
- Do NOT use peer-to-peer agent discussion (expensive, redundant). Use strict hierarchical flow: analysts → manager only.
- Three-layer memory is essential: **working** (current state), **procedural** (past decisions with timeliness decay), **episodic** (manager's P&L-linked beliefs).
- The key innovation is **Conceptual Verbal Reinforcement (CVRF)**: after each decision cycle, compare profitable vs unprofitable trajectories, extract "investment beliefs" in plain text, and propagate those beliefs selectively to relevant agents only. This mimics gradient descent without training.
- Within-cycle risk: CVaR threshold monitoring triggers real-time self-reflection. Over-cycle risk: CVRF belief updates across runs.
- Converges in ~4 episodes (vs thousands for DRL). Sample efficient.

### Benchmarking Paper → Architecture Choice + SEC Ingestion
- Of four architectures tested (sequential, parallel, hierarchical, reflexive): **hierarchical wins** on accuracy/cost balance.
- Reflexive architecture (agent self-critiques its own output) adds 5–15% accuracy but doubles cost — use it **selectively** only on low-confidence or high-stakes decisions, not by default.
- For financial document ingestion (SEC filings): hierarchical extraction works best — a supervisor delegates to specialized sub-agents (metrics extractor, risk-factors extractor, MD&A extractor), then aggregates.
- **Cascading errors** are the primary failure mode — validate outputs at each stage with structured JSON schemas to prevent garbage propagating downstream.
- Use RAGAS-style evaluation framework to measure quality of extraction and reasoning.

### D3 → Upgrade the Debate Layer
- Replace the single "Debate Judge" node with a **3-stage D3 pipeline**:
  1. **Debate**: Bull and Bear agents alternate turns presenting arguments (2–3 rounds). Each sees opponent's prior argument before responding.
  2. **Deliberate**: Both agents receive the **full debate transcript** and must reconsider/strengthen their position. Forces deeper reasoning.
  3. **Decide**: Judge evaluates with **cost-awareness** — if one side clearly dominates, fast decision. If ambiguous, escalate to a deeper analysis prompt or an additional round.
- This is not just a design nicety — D3 measurably improves calibration and reduces variance in financial judgments vs single-pass evaluation.
- Tie-breaking: if debate stays ambiguous after deliberation, defer to Risk Manager's assessment.

---

## Free / Open-Source Tech Stack

| Component | Choice | Why |
|---|---|---|
| Orchestration | LangGraph (open-source) | User's requirement |
| LLM | Groq API free tier (Llama 3.3 70B) | Fastest free inference, strong reasoning |
| LLM fallback | Google Gemini 2.0 Flash (free tier) | Backup for rate limits |
| Embeddings | sentence-transformers local (all-MiniLM-L6-v2) | Fully local, no API cost |
| Vector DB | ChromaDB (local) | Free, persistent, LangChain-native |
| Episodic memory | SQLite | Simple, local, no cost |
| Stock data | yfinance | Free, covers OHLCV + fundamentals |
| SEC filings | sec-edgar-downloader + EDGAR REST API | Free, official |
| News | NewsAPI free tier (100 req/day) | Sufficient for dev/demo |
| Reddit sentiment | PRAW (Reddit API, free) | r/investing, r/stocks |
| Technical indicators | pandas-ta | Free, 150+ indicators |
| Evaluation | Custom RAGAS-inspired metrics | Free |

---

## Architecture — 8-Node Graph

> Optimised for free-tier token limits: 8 LLM calls/run, ~11K tokens/run.
> Provider split: 8B model for volume nodes, 70B for quality-critical nodes.

```
User Query ("Analyze NVDA")
    │
    ▼
Supervisor                         ← no LLM · loads memory + beliefs
    │
    ├──────────────────────────────┐──────────────────────────────┐
    ▼                              ▼                              ▼
Fundamental Agent          Technical Agent               Sentiment Agent
(SEC EDGAR + yfinance)     (pandas-ta indicators)        (NewsAPI)
[8B · ~800 tok out]        [8B · ~800 tok out]           [8B · ~800 tok out]
    │                              │                              │
    └──────────────────────────────┴──────────────────────────────┘
                                   │
                                   ▼
                          Research Synthesizer
                          (merges 3 inputs, validates JSON)
                          [70B · ~900 tok out]
                                   │
                                   ▼
                          Debate Agent                   ← SINGLE combined call
                          (bull case + bear case +
                           rebuttals + winner in one prompt)
                          [8B · ~1200 tok out]
                                   │
                                   ▼
                          Risk Manager
                          (CVaR + vol ratio · sets risk_flag)
                          [70B · ~600 tok out]
                                   │
                          [conditional routing]
                          ┌────────┴────────┐
                          │                 │
                     RISK FLAG          CLEAR
                     → Supervisor    → Final Decision
                                          │
                                          ▼
                                   Final Decision
                                   (BUY/HOLD/SELL · stores to DB)
                                   [70B · ~700 tok out]
                                          │
                                          ▼
                                   Reflection              ← CVRF (FINCON)
                                   (extracts beliefs · writes to SQLite)
                                   [8B · ~400 tok out]
```

**Token budget per run:**
| Model | Nodes | Calls | ~Tokens | Daily pool |
|-------|-------|-------|---------|-----------|
| llama-3.1-8b-instant | fundamental, technical, sentiment, debate, reflection | 5 | ~5K | 500K |
| llama-3.3-70b-versatile | synthesizer, risk_manager, final_decision | 3 | ~2.2K | 100K |

---

## Project File Structure

```
AI_Hedge_Fund/
├── src/
│   ├── agents/
│   │   ├── supervisor.py          # state init, memory injection (no LLM)
│   │   ├── fundamental.py         # SEC EDGAR + yfinance financials · 8B
│   │   ├── technical.py           # pandas-ta (RSI, MACD, Bollinger, ATR) · 8B
│   │   ├── sentiment.py           # NewsAPI headlines · 8B
│   │   ├── synthesizer.py         # hierarchical aggregation + JSON validation · 70B
│   │   ├── debate.py              # bull+bear+rebuttal+winner in one call · 8B
│   │   ├── risk_manager.py        # CVaR + vol + concentration checks · 70B
│   │   ├── final_decision.py      # BUY/HOLD/SELL output · 70B
│   │   ├── reflection.py          # CVRF belief extraction · 8B
│   │   └── llm_client.py          # provider routing + rate guard + max_tokens
│   ├── graph/
│   │   ├── state.py               # TypedDict LangGraph state schema
│   │   ├── workflow.py            # graph assembly + node wiring
│   │   └── routing.py             # conditional edge functions
│   ├── memory/
│   │   ├── working_memory.py      # in-graph state (LangGraph handles this)
│   │   ├── procedural_memory.py   # ChromaDB with timeliness decay scoring
│   │   └── episodic_memory.py     # SQLite: past decisions + extracted beliefs
│   ├── tools/
│   │   ├── yfinance_tool.py       # OHLCV, fundamentals, vol data
│   │   ├── sec_edgar_tool.py      # 10-K/10-Q downloader + section extractor
│   │   ├── news_tool.py           # NewsAPI fetcher
│   │   └── technical_tool.py      # pandas-ta indicator calculator
│   └── config.py                  # API keys, model names, thresholds
├── main.py                        # entrypoint: run analysis for a ticker
├── evaluate.py                    # RAGAS-inspired quality metrics
└── requirements.txt
```

---

## LangGraph State Schema

```python
class HedgeFundState(TypedDict):
    # Input
    ticker: str
    user_query: str

    # Research outputs (structured JSON from each agent)
    fundamental_analysis: dict
    technical_analysis: dict
    sentiment_analysis: dict
    synthesized_research: dict

    # D3 debate state
    bull_case_round1: str
    bear_case_round1: str
    bull_rebuttal: str
    bear_rebuttal: str
    deliberation_bull: str
    deliberation_bear: str
    debate_summary: dict          # judge output: winner, confidence, reasoning
    debate_ambiguous: bool        # triggers escalation path

    # Risk + decision
    risk_analysis: dict           # CVaR, vol, flags
    risk_flag: bool               # routes back to supervisor if True
    final_decision: dict          # action, confidence, explanation

    # Memory context (injected by supervisor at start)
    past_decisions: list          # from procedural memory (ChromaDB)
    investment_beliefs: list      # from episodic memory (SQLite CVRF beliefs)

    # Reflection output (written back to memory at end)
    new_beliefs: list
```

---

## Key Implementation Details

### 1. CVRF Reflection (reflection.py)
After each completed decision cycle:
1. Load last N decisions + outcomes from SQLite episodic memory.
2. Prompt LLM: *"Given these profitable decisions [X] and unprofitable decisions [Y], what investment beliefs should guide future analysis of this sector/asset type?"*
3. Extract 3–5 concise belief statements (e.g., "RSI divergence matters more than absolute RSI level for TSLA").
4. Determine which agents each belief is relevant to (fundamental/technical/sentiment).
5. Store beliefs in SQLite with timestamp + relevant_agents list.
6. Supervisor injects relevant beliefs into each agent's system prompt at next run.

### 2. Timeliness Decay in Procedural Memory (procedural_memory.py)
When retrieving past analysis from ChromaDB:
```
decay_score = base_similarity * exp(-λ * days_since_stored)
λ = 0.05  # half-life ~14 days for market data
```
Rank by `decay_score` not raw similarity. Prevents old market regimes from dominating.

### 3. D3 Cost-Aware Routing (routing.py)
```python
def route_after_debate(state):
    if state["debate_summary"]["confidence"] > 0.75:
        return "risk_manager"        # clear winner → fast path
    elif state["debate_rounds"] < 2:
        return "deliberation"        # ambiguous → deliberation round
    else:
        return "risk_manager"        # after deliberation, proceed regardless
```

### 4. CVaR Risk Check (risk_manager.py)
- Fetch 252 days of daily returns via yfinance.
- CVaR (95%) = mean of worst 5% daily returns.
- If CVaR < -3% AND current position would be BUY → flag for supervisor review.
- Also check: 30-day vol > 2x sector average → flag.

### 5. JSON Validation Gate (synthesizer.py)
Each upstream agent must return a structured dict matching a Pydantic schema. If any agent returns malformed output:
- Log the failure.
- Re-prompt that agent once with error message.
- If second attempt fails, mark that analysis as `null` with a confidence penalty on final decision.
This prevents cascading errors (key finding from Benchmarking paper).

---

## Build Order (Phase by Phase)

### Phase 1 — Scaffold + Tools
1. `config.py` with env vars and model config
2. `tools/` — yfinance, pandas-ta, NewsAPI, Reddit, SEC EDGAR
3. `graph/state.py` — full TypedDict state

### Phase 2 — Research Agents
4. `agents/fundamental.py`, `technical.py`, `sentiment.py`
5. `agents/synthesizer.py` with Pydantic validation

### Phase 3 — D3 Debate Layer
6. `agents/bull.py`, `bear.py` (turn-taking, each reads opponent's arg)
7. `agents/deliberation.py` (full transcript reconsideration)
8. `agents/debate_judge.py` (cost-aware fast/slow path)
9. `graph/routing.py` with debate confidence routing

### Phase 4 — Risk + Decision
10. `agents/risk_manager.py` with CVaR
11. `agents/final_decision.py`

### Phase 5 — Memory + CVRF
12. `memory/procedural_memory.py` (ChromaDB + decay)
13. `memory/episodic_memory.py` (SQLite + beliefs)
14. `agents/reflection.py` (CVRF belief extraction)
15. Update `agents/supervisor.py` to inject beliefs

### Phase 6 — Graph Assembly + Entrypoint
16. `graph/workflow.py` — wire all nodes and edges
17. `main.py` — CLI entrypoint
18. `evaluate.py` — basic quality metrics

---

## Verification / Testing Plan

1. **Unit test each tool**: run `yfinance_tool.py` standalone for NVDA, check OHLCV returns.
2. **Unit test each agent**: call each agent node with a mock state dict, verify output matches Pydantic schema.
3. **Test D3 debate in isolation**: run bull → bear → deliberation → judge for NVDA, print full transcript, verify judge produces structured output.
4. **End-to-end run**: `python main.py --ticker NVDA` and trace full graph execution via LangGraph's built-in visualization.
5. **Memory persistence test**: run twice for same ticker, verify second run has procedural memory populated and decay scoring is applied.
6. **CVRF test**: manually inject two contrasting past decisions (one profitable, one not), run reflection agent, verify it generates at least 2 belief statements.
7. **Risk flag routing test**: mock a state with high CVaR, verify graph routes back to supervisor instead of proceeding to final decision.

---

## What This System Does Better Than Basic Multi-Agent

| Naive approach | This system (paper-informed) |
|---|---|
| Single debate round | D3: 3-stage debate with deliberation + cost-aware escalation |
| All agents talk to each other | Hierarchical only: analysts → manager, no peer chatter |
| Simple RAG memory | 3-layer memory with timeliness decay + CVRF belief evolution |
| Static prompts | Dynamic belief injection per agent per run (CVRF) |
| No error handling | Pydantic validation gates, single retry, confidence penalty |
| No risk integration | CVaR + volatility gates with conditional routing |
| One-shot LLM calls | Reflexive self-critique on low-confidence outputs |
