"""
Risk Manager Agent.
Evaluates downside risk using CVaR (FINCON-inspired within-cycle risk control).
Flags: CVaR > threshold, volatility > 2x sector, high concentration risk.
Conditional routing: risk_flag=True routes back to supervisor for re-evaluation.
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, ValidationError

from src.graph.state import HedgeFundState
from src.agents.llm_client import get_llm
from src.tools.yfinance_tool import get_volatility_metrics, get_sector_volatility
from src.config import CVAR_THRESHOLD, VOL_MULTIPLIER_THRESHOLD


class RiskOutput(BaseModel):
    risk_level: str                # 'low' | 'moderate' | 'high' | 'extreme'
    cvar_flag: bool
    volatility_flag: bool
    concentration_flag: bool       # True if stock is highly correlated with broad market
    overall_risk_flag: bool        # True = route back to supervisor
    risk_factors: list[str]
    risk_mitigation: list[str]     # suggestions if proceeding despite risk
    position_size_suggestion: str  # e.g. "reduce to 2% of portfolio"
    summary: str


SYSTEM_PROMPT = """You are a risk manager responsible for protecting capital.
Analyze the quantitative risk metrics and debate outcome to assess overall investment risk.
Output ONLY a JSON object matching this exact schema — no markdown, no explanation outside JSON:
{{
  "risk_level": "<low|moderate|high|extreme>",
  "cvar_flag": <true|false>,
  "volatility_flag": <true|false>,
  "concentration_flag": <true|false>,
  "overall_risk_flag": <true|false>,
  "risk_factors": ["<factor1>", "<factor2>"],
  "risk_mitigation": ["<mitigation1>", "<mitigation2>"],
  "position_size_suggestion": "<suggestion>",
  "summary": "<2-3 sentence risk summary>"
}}
Set overall_risk_flag to true only if risk is HIGH or EXTREME and the debate outcome is not strongly convincing."""


def risk_manager_node(state: HedgeFundState) -> dict:
    ticker = state["ticker"]
    debate_summary = state.get("debate_result", {})
    synthesis = state.get("synthesized_research", {})

    # Fetch quantitative risk metrics
    vol_metrics = get_volatility_metrics(ticker)
    sector_vol = get_sector_volatility(ticker)

    cvar = vol_metrics.get("cvar_95", 0)
    vol_ratio = sector_vol.get("vol_ratio", 1.0)

    # Hard thresholds (from config)
    cvar_flag = cvar < CVAR_THRESHOLD  # e.g. cvar < -0.03
    vol_flag = (vol_ratio or 0) > VOL_MULTIPLIER_THRESHOLD

    user_msg = f"""Stock: {ticker}

Quantitative Risk Metrics:
- CVaR (95%): {cvar:.4f} (threshold: {CVAR_THRESHOLD})
- CVaR flag triggered: {cvar_flag}
- Annualized Volatility: {vol_metrics.get('annualized_vol', 'N/A')}
- 30-day Volatility: {vol_metrics.get('vol_30d', 'N/A')}
- Sector ({sector_vol.get('sector', 'N/A')}) ETF vol: {sector_vol.get('sector_vol_30d', 'N/A')}
- Vol ratio vs sector: {vol_ratio:.2f}x (threshold: {VOL_MULTIPLIER_THRESHOLD}x)
- Vol flag triggered: {vol_flag}
- Max Drawdown: {vol_metrics.get('max_drawdown', 'N/A')}

Debate Outcome:
- Winner: {debate_summary.get('winner', 'N/A')}
- Confidence: {debate_summary.get('confidence', 'N/A')}
- Investment lean: {debate_summary.get('investment_lean', 'N/A')}
- Winner reasoning: {debate_summary.get('winner_reasoning', 'N/A')}

Research Context:
- Overall signal: {synthesis.get('overall_signal', 'N/A')}
- Signal alignment: {synthesis.get('signal_alignment', 'N/A')}
- Data quality: {synthesis.get('data_quality', 'N/A')}
- Key uncertainties: {synthesis.get('key_uncertainties', [])}

Assess overall investment risk and determine if this decision should be flagged for re-evaluation. Output as JSON."""

    llm = get_llm("risk")
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
        validated = RiskOutput(**parsed)
        result = validated.model_dump()
        return {
            "risk_analysis": result,
            "risk_flag": validated.overall_risk_flag,
        }
    except (json.JSONDecodeError, ValidationError) as e:
        # On parse failure, default to flagging for safety
        return {
            "risk_analysis": {"risk_level": "unknown", "summary": f"Parse error: {e}"},
            "risk_flag": cvar_flag or vol_flag,
            "agent_errors": [f"risk_manager: {e}"],
        }
