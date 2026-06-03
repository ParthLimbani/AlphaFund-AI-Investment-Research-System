"""
Technical Analyst Agent.
Computes indicators via pandas-ta then uses LLM to interpret them.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm
from src.tools.technical_tool import get_technical_indicators


class TechnicalOutput(BaseModel):
    trend: str                 # 'bullish' | 'bearish' | 'neutral'
    momentum: str              # 'strong' | 'moderate' | 'weak' | 'negative'
    support_level: float | None
    resistance_level: float | None
    key_signals: list[str]     # e.g. ["RSI oversold", "MACD bullish crossover"]
    summary: str
    confidence: float


SYSTEM_PROMPT = """You are a technical analyst specializing in momentum and trend analysis.
Analyze the provided technical indicators for the given stock.
Output ONLY a JSON object matching this exact schema — no markdown, no explanation outside JSON:
{{
  "trend": "<bullish|bearish|neutral>",
  "momentum": "<strong|moderate|weak|negative>",
  "support_level": <price_float_or_null>,
  "resistance_level": <price_float_or_null>,
  "key_signals": ["<signal1>", "<signal2>", "<signal3>"],
  "summary": "<2-3 sentence technical summary>",
  "confidence": <0.0-1.0>
}}"""


def technical_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    beliefs = state.get("investment_beliefs", [])

    indicators = get_technical_indicators(ticker)
    if "error" in indicators:
        return {
            "technical_analysis": {},
            "agent_errors": [f"technical_agent: {indicators['error']}"],
        }

    belief_context = ""
    if beliefs:
        belief_context = "\n\nRelevant investment beliefs:\n" + "\n".join(
            f"- {b}" for b in beliefs[:3]
        )

    user_msg = f"""Ticker: {ticker}

Technical Indicators:
{json.dumps(indicators, indent=2, default=str)}
{belief_context}

Provide your technical analysis as JSON."""

    llm = get_llm("analyst")
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
        validated = TechnicalOutput(**parsed)
        return {"technical_analysis": validated.model_dump()}
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
            validated2 = TechnicalOutput(**json.loads(raw2.strip()))
            return {"technical_analysis": validated2.model_dump()}
        except Exception as e2:
            return {
                "technical_analysis": {},
                "agent_errors": [f"technical_agent: {e2}"],
            }
