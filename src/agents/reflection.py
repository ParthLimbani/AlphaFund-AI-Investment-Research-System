"""
Reflection Agent — CVRF (Conceptual Verbal Reinforcement Framework) from FINCON.
After each decision cycle, extracts investment beliefs by comparing patterns
across recent decisions. Beliefs are stored in episodic memory and injected
into downstream agents on the next run via the supervisor.

Key idea from FINCON: "textual gradient descent" — LLM reflects on profitable
vs unprofitable trajectories and extracts conceptualized investment insights
that guide future agent behavior.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm
from src.memory.episodic_memory import (
    get_recent_decisions, store_belief, get_beliefs
)
from src.config import CVRF_LOOKBACK_DECISIONS, CVRF_MAX_BELIEFS


SYSTEM_PROMPT = """You are a meta-analyst responsible for extracting investment beliefs from past decision patterns.
You will be given a history of investment decisions and their outcomes.
Your job is to extract concise, actionable investment beliefs — patterns or rules that should guide future analysis.

For each belief:
- Make it specific and actionable (e.g., "Technical momentum signals are more predictive than RSI alone for high-beta tech stocks")
- Identify which agents should receive this belief (fundamental, technical, sentiment, or all)
- Only extract beliefs supported by multiple data points — no single-decision generalizations

Output ONLY a JSON array of belief objects — no markdown, no explanation outside JSON:
[
  {{
    "belief": "<specific actionable belief>",
    "relevant_agents": ["<agent1>", "<agent2>"],
    "rationale": "<1 sentence why this belief was extracted>"
  }},
  ...
]
Extract at most {max_beliefs} beliefs. If there are insufficient data points, return an empty array []."""


def reflection_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    current_decision = state.get("final_decision", {})

    # Load recent decision history for this ticker
    recent_decisions = get_recent_decisions(ticker, limit=CVRF_LOOKBACK_DECISIONS)

    if len(recent_decisions) < 2:
        # Not enough history to extract meaningful beliefs yet
        return {"new_beliefs": []}

    # Format decision history for LLM
    history_text = "\n\n".join([
        f"Decision {i+1} [{d.get('created_at', '')[:10]}]:\n"
        f"  Action: {d.get('action')}\n"
        f"  Confidence: {d.get('confidence')}\n"
        f"  Risk flag was set: {bool(d.get('risk_flag'))}\n"
        f"  Debate winner: {d.get('debate_winner', 'N/A')}\n"
        f"  Explanation: {d.get('explanation', '')[:300]}"
        for i, d in enumerate(recent_decisions)
    ])

    # Current cycle context
    current_context = f"""Current Decision:
  Action: {current_decision.get('action')}
  Confidence: {current_decision.get('confidence')}
  Key reasons: {current_decision.get('key_reasons', [])}
  Key risks: {current_decision.get('key_risks', [])}"""

    # Existing beliefs (to avoid duplicates)
    existing_beliefs = [b["belief"] for b in get_beliefs(ticker=ticker, limit=10)]
    existing_text = "\n".join(f"- {b}" for b in existing_beliefs) or "None yet."

    user_msg = f"""Ticker: {ticker}

Recent Decision History:
{history_text}

{current_context}

Existing Beliefs (do not duplicate):
{existing_text}

Extract new investment beliefs from these patterns. Output as JSON array."""

    llm = get_llm("analyst")
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT.format(max_beliefs=CVRF_MAX_BELIEFS)),
        HumanMessage(content=user_msg),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        beliefs_raw = json.loads(raw)
        if not isinstance(beliefs_raw, list):
            return {"new_beliefs": []}

        new_belief_texts = []
        decision_ids = [d.get("id") for d in recent_decisions if d.get("id")]

        for item in beliefs_raw[:CVRF_MAX_BELIEFS]:
            belief_text = item.get("belief", "").strip()
            relevant_agents = item.get("relevant_agents", ["all"])
            if belief_text:
                store_belief(
                    ticker=ticker,
                    belief=belief_text,
                    relevant_agents=relevant_agents,
                    source_decision_ids=decision_ids,
                )
                new_belief_texts.append(belief_text)

        return {"new_beliefs": new_belief_texts}

    except Exception:
        return {"new_beliefs": []}
