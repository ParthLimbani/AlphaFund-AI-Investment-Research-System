"""
Supervisor Agent — entry node of the LangGraph.
Responsibilities:
- Initialize and validate state
- Load working memory context (past decisions + CVRF beliefs from episodic/procedural memory)
- Inject relevant beliefs into state so downstream agents can use them
- Re-entry point if risk_flag is raised by risk manager
"""
from datetime import datetime, timezone

from src.graph.state import HedgeFundState
from src.memory.procedural_memory import retrieve_past_decisions
from src.memory.episodic_memory import get_beliefs, get_recent_decisions


def supervisor_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]

    # Load procedural memory: past analysis with timeliness decay
    past_decisions = retrieve_past_decisions(ticker, top_k=5)

    # Load episodic memory: CVRF-extracted investment beliefs for this ticker
    beliefs = get_beliefs(ticker=ticker, limit=10)
    belief_texts = [b["belief"] for b in beliefs]

    # Also pull recent decision history for the reflection agent
    recent = get_recent_decisions(ticker, limit=5)

    return {
        "past_decisions": past_decisions,
        "investment_beliefs": belief_texts,
        "agent_errors": [],
        # Reset debate state on re-entry after risk_flag
        "debate_rounds_done": state.get("debate_rounds_done", 0),
        "risk_flag": False,
    }
