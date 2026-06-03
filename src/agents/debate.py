"""
Debate Agent — combined bull case, bear case, rebuttal, and winner in one LLM call.
Replaces the previous 5-node debate pipeline (bull_round1, bear_round1,
bull_rebuttal, bear_rebuttal, deliberation, debate_judge).
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm


class DebateOutput(BaseModel):
    bull_case: str          # 3 strongest arguments for buying
    bear_case: str          # 3 strongest arguments against buying
    bull_rebuttal: str      # bull's counter to bear's weakest points
    bear_rebuttal: str      # bear's counter to bull's weakest points
    winner: str             # 'bull' | 'bear' | 'draw'
    winner_reasoning: str   # 2-sentence explanation of who won and why
    confidence: float       # 0.0–1.0 decisiveness of the outcome
    investment_lean: str    # 'bullish' | 'neutral' | 'bearish'


SYSTEM_PROMPT = """You are conducting a structured investment debate on a stock.
Based on the research provided, generate both sides of the argument and declare a winner.
Be objective — let the evidence determine the winner, not bias.
Output ONLY a JSON object matching this exact schema — no markdown, no explanation outside JSON:
{{
  "bull_case": "<3 concise arguments for buying, separated by | >",
  "bear_case": "<3 concise arguments against buying, separated by | >",
  "bull_rebuttal": "<bull counters the 2 weakest bear points>",
  "bear_rebuttal": "<bear counters the 2 weakest bull points>",
  "winner": "<bull|bear|draw>",
  "winner_reasoning": "<2 sentences explaining which case was stronger and why>",
  "confidence": <0.0-1.0>,
  "investment_lean": "<bullish|neutral|bearish>"
}}"""


def debate_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    synthesis = state.get("synthesized_research", {})
    beliefs = state.get("investment_beliefs", [])

    belief_context = ""
    if beliefs:
        belief_context = "\nRelevant past beliefs:\n" + "\n".join(
            f"- {b}" for b in beliefs[:3]
        )

    user_msg = f"""Stock: {ticker}

Research Summary:
- Overall signal: {synthesis.get('overall_signal', 'N/A')}
- Signal alignment: {synthesis.get('signal_alignment', 'N/A')}
- Bull arguments from research: {synthesis.get('bull_arguments', [])}
- Bear arguments from research: {synthesis.get('bear_arguments', [])}
- Key uncertainties: {synthesis.get('key_uncertainties', [])}
- Data quality: {synthesis.get('data_quality', 'N/A')}
- Fundamental signal: {synthesis.get('fundamental_signal', 'N/A')}
- Technical signal: {synthesis.get('technical_signal', 'N/A')}
- Sentiment signal: {synthesis.get('sentiment_signal', 'N/A')}
{belief_context}

Generate the structured debate and declare a winner. Output as JSON."""

    llm = get_llm("debate")
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
        validated = DebateOutput(**parsed)
        return {"debate_result": validated.model_dump()}
    except (json.JSONDecodeError, ValidationError) as e:
        retry_msg = f"Invalid response: {e}. Output ONLY the JSON object."
        response2 = llm.invoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
            HumanMessage(content=retry_msg),
        ])
        raw2 = response2.content.strip()
        if raw2.startswith("```"):
            raw2 = raw2.split("```")[1]
            if raw2.startswith("json"):
                raw2 = raw2[4:]
        try:
            validated2 = DebateOutput(**json.loads(raw2.strip()))
            return {"debate_result": validated2.model_dump()}
        except Exception as e2:
            return {
                "debate_result": {
                    "bull_case": "N/A", "bear_case": "N/A",
                    "bull_rebuttal": "N/A", "bear_rebuttal": "N/A",
                    "winner": "draw", "winner_reasoning": "Debate failed to parse.",
                    "confidence": 0.5, "investment_lean": "neutral",
                },
                "agent_errors": [f"debate: {e2}"],
            }
