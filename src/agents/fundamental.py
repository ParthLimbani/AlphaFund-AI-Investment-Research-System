"""
Fundamental Analyst Agent.
Fetches yfinance financials + SEC 10-K, then uses LLM to produce
a structured fundamental analysis dict.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm
from src.tools.yfinance_tool import get_fundamentals
from src.tools.sec_edgar_tool import get_latest_10k_summary


class FundamentalOutput(BaseModel):
    valuation_signal: str          # 'undervalued' | 'fairly_valued' | 'overvalued'
    financial_health: str          # 'strong' | 'moderate' | 'weak'
    growth_outlook: str            # 'high' | 'moderate' | 'low' | 'negative'
    key_strengths: list[str]
    key_risks: list[str]
    summary: str
    confidence: float              # 0.0 – 1.0


SYSTEM_PROMPT = """You are a fundamental equity analyst with expertise in financial statement analysis and valuation.
Analyze the provided financial data and SEC filing information for the given stock.
Output ONLY a JSON object matching this exact schema — no markdown, no explanation outside JSON:
{{
  "valuation_signal": "<undervalued|fairly_valued|overvalued>",
  "financial_health": "<strong|moderate|weak>",
  "growth_outlook": "<high|moderate|low|negative>",
  "key_strengths": ["<strength1>", "<strength2>", "<strength3>"],
  "key_risks": ["<risk1>", "<risk2>", "<risk3>"],
  "summary": "<2-3 sentence fundamental summary>",
  "confidence": <0.0-1.0>
}}"""


def fundamental_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    beliefs = state.get("investment_beliefs", [])

    # Fetch raw data
    fundamentals = get_fundamentals(ticker)
    sec_data = get_latest_10k_summary(ticker)

    # Build belief injection string
    belief_context = ""
    if beliefs:
        belief_context = "\n\nRelevant investment beliefs from past analysis:\n" + "\n".join(
            f"- {b}" for b in beliefs[:3]
        )

    user_msg = f"""Ticker: {ticker}

Financial Metrics:
{json.dumps(fundamentals, indent=2, default=str)}

SEC 10-K Summary:
- Business: {sec_data.get('business_description', 'N/A')[:1000]}
- Risk Factors: {sec_data.get('risk_factors', 'N/A')[:800]}
- MD&A: {sec_data.get('mda_highlights', 'N/A')[:800]}
{belief_context}

Provide your fundamental analysis as JSON."""

    llm = get_llm("analyst")
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    raw = response.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
        validated = FundamentalOutput(**parsed)
        return {"fundamental_analysis": validated.model_dump()}
    except (json.JSONDecodeError, ValidationError) as e:
        # Retry once with explicit error feedback
        retry_msg = f"Your previous response was invalid JSON or failed schema validation: {e}\nPlease output ONLY the JSON object, no other text."
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
            parsed2 = json.loads(raw2.strip())
            validated2 = FundamentalOutput(**parsed2)
            return {"fundamental_analysis": validated2.model_dump()}
        except Exception as e2:
            return {
                "fundamental_analysis": {},
                "agent_errors": [f"fundamental_agent: {e2}"],
            }
