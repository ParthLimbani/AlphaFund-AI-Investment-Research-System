"""
Final Decision Agent.
Synthesizes all upstream outputs into a BUY / HOLD / SELL decision
with confidence score and plain-English explanation.
Also triggers storage of the decision into procedural + episodic memory.
"""
import json
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm
from src.memory.procedural_memory import store_analysis
from src.memory.episodic_memory import store_decision


class DecisionOutput(BaseModel):
    action: str                    # 'BUY' | 'HOLD' | 'SELL'
    confidence: float              # 0.0 – 1.0
    time_horizon: str              # 'short_term' | 'medium_term' | 'long_term'
    price_target: str              # e.g. "$150-170 over 12 months" or "N/A"
    key_reasons: list[str]         # top 3 reasons for the decision
    key_risks: list[str]           # top 2 risks to the thesis
    explanation: str               # 3-4 sentence plain-English explanation


SYSTEM_PROMPT = """You are the final investment decision maker for an AI hedge fund.
You have access to research analysis, a structured bull/bear debate, and a risk assessment.
Your job is to make a clear, justified investment decision.
Output ONLY a JSON object matching this exact schema — no markdown, no explanation outside JSON:
{{
  "action": "<BUY|HOLD|SELL>",
  "confidence": <0.0-1.0>,
  "time_horizon": "<short_term|medium_term|long_term>",
  "price_target": "<target string or N/A>",
  "key_reasons": ["<reason1>", "<reason2>", "<reason3>"],
  "key_risks": ["<risk1>", "<risk2>"],
  "explanation": "<3-4 sentence explanation>"
}}"""


def final_decision_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    synthesis = state.get("synthesized_research", {})
    debate = state.get("debate_result", {})
    risk = state.get("risk_analysis", {})
    past_decisions = state.get("past_decisions", [])
    beliefs = state.get("investment_beliefs", [])

    past_context = ""
    if past_decisions:
        past_context = "\n\nPast decisions for this ticker (timeliness-decay ranked):\n" + "\n".join(
            f"- [{p.get('stored_at', '')[:10]}] {p.get('content', {}).get('action', 'N/A')} "
            f"(confidence: {p.get('content', {}).get('confidence', 'N/A')}) "
            f"decay_score: {p.get('decay_score', 'N/A')}"
            for p in past_decisions[:3]
        )

    belief_context = ""
    if beliefs:
        belief_context = "\n\nInvestment beliefs from prior cycles:\n" + "\n".join(
            f"- {b}" for b in beliefs[:5]
        )

    user_msg = f"""Stock: {ticker}

Research Synthesis:
- Overall signal: {synthesis.get('overall_signal', 'N/A')}
- Signal alignment: {synthesis.get('signal_alignment', 'N/A')}
- Bull arguments: {synthesis.get('bull_arguments', [])}
- Bear arguments: {synthesis.get('bear_arguments', [])}
- Key uncertainties: {synthesis.get('key_uncertainties', [])}

Debate Outcome:
- Winner: {debate.get('winner', 'N/A')}
- Confidence: {debate.get('confidence', 'N/A')}
- Investment lean: {debate.get('investment_lean', 'N/A')}
- Bull case: {debate.get('bull_case', 'N/A')}
- Bear case: {debate.get('bear_case', 'N/A')}
- Winner reasoning: {debate.get('winner_reasoning', 'N/A')}

Risk Assessment:
- Risk level: {risk.get('risk_level', 'N/A')}
- Risk factors: {risk.get('risk_factors', [])}
- Position size suggestion: {risk.get('position_size_suggestion', 'N/A')}
{past_context}{belief_context}

Make your final investment decision. Output as JSON."""

    llm = get_llm("judge")
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
        validated = DecisionOutput(**parsed)
        result = validated.model_dump()
        result["ticker"] = ticker
        result["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Persist to procedural memory (ChromaDB)
        store_analysis(ticker, "decision", result)

        # Persist to episodic memory (SQLite)
        store_decision(
            ticker=ticker,
            action=validated.action,
            confidence=validated.confidence,
            explanation=validated.explanation,
            debate_winner=debate.get("winner"),
            risk_flag=state.get("risk_flag", False),
        )

        return {"final_decision": result}

    except (json.JSONDecodeError, ValidationError) as e:
        fallback = {
            "action": "HOLD",
            "confidence": 0.3,
            "time_horizon": "medium_term",
            "price_target": "N/A",
            "key_reasons": ["Insufficient data to make a confident decision"],
            "key_risks": ["Parse error in decision agent"],
            "explanation": f"Decision agent encountered a parsing error: {e}. Defaulting to HOLD.",
            "ticker": ticker,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {
            "final_decision": fallback,
            "agent_errors": [f"final_decision: {e}"],
        }
