"""
Research Synthesizer Agent.
Hierarchically aggregates outputs from fundamental, technical, and sentiment agents.
Validates all three inputs (cascading error prevention from Benchmarking paper).
Produces a unified investment context for the debate layer.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm


class SynthesisOutput(BaseModel):
    overall_signal: str            # 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell'
    signal_alignment: str          # 'aligned' | 'mixed' | 'conflicted'
    fundamental_weight: float      # relative weight (0-1, sums to 1 with others)
    technical_weight: float
    sentiment_weight: float
    bull_arguments: list[str]      # 3-5 strongest bullish points across all research
    bear_arguments: list[str]      # 3-5 strongest bearish points across all research
    key_uncertainties: list[str]   # main unknowns that could flip the thesis
    investment_context: str        # 3-4 sentence synthesized narrative
    data_quality: str              # 'high' | 'medium' | 'low' (based on what data was available)


SYSTEM_PROMPT = """You are a senior investment strategist who synthesizes research from multiple analyst teams.
Your job is to combine fundamental, technical, and sentiment analysis into a coherent investment thesis.
Note any missing data or low-confidence inputs and adjust data_quality accordingly.
Output ONLY a JSON object matching this exact schema — no markdown, no explanation outside JSON:
{{
  "overall_signal": "<strong_buy|buy|hold|sell|strong_sell>",
  "signal_alignment": "<aligned|mixed|conflicted>",
  "fundamental_weight": <0.0-1.0>,
  "technical_weight": <0.0-1.0>,
  "sentiment_weight": <0.0-1.0>,
  "bull_arguments": ["<arg1>", "<arg2>", "<arg3>"],
  "bear_arguments": ["<arg1>", "<arg2>", "<arg3>"],
  "key_uncertainties": ["<uncertainty1>", "<uncertainty2>"],
  "investment_context": "<3-4 sentence synthesis>",
  "data_quality": "<high|medium|low>"
}}
Note: fundamental_weight + technical_weight + sentiment_weight should sum to ~1.0."""


def synthesizer_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    fundamental = state.get("fundamental_analysis", {})
    technical = state.get("technical_analysis", {})
    sentiment = state.get("sentiment_analysis", {})
    errors = state.get("agent_errors", [])

    # Assess data quality based on what was successfully retrieved
    missing = []
    if not fundamental:
        missing.append("fundamental")
    if not technical:
        missing.append("technical")
    if not sentiment:
        missing.append("sentiment")

    data_note = f"Note: Missing data from: {', '.join(missing)}" if missing else "All three research streams available."

    user_msg = f"""Ticker: {ticker}
{data_note}

Fundamental Analysis:
{json.dumps(fundamental, indent=2) if fundamental else "UNAVAILABLE"}

Technical Analysis:
{json.dumps(technical, indent=2) if technical else "UNAVAILABLE"}

Sentiment Analysis:
{json.dumps(sentiment, indent=2) if sentiment else "UNAVAILABLE"}

Agent errors encountered: {errors if errors else "None"}

Synthesize all available research into a unified investment thesis. Output as JSON."""

    llm = get_llm("synthesis")
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
        validated = SynthesisOutput(**parsed)
        return {"synthesized_research": validated.model_dump()}
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
            validated2 = SynthesisOutput(**json.loads(raw2.strip()))
            return {"synthesized_research": validated2.model_dump()}
        except Exception as e2:
            return {
                "synthesized_research": {},
                "agent_errors": [f"synthesizer_agent: {e2}"],
            }
