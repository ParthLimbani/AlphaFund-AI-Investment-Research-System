"""
Conditional edge routing for the LangGraph workflow.
"""
from src.graph.state import HedgeFundState


def route_after_risk(state: HedgeFundState) -> str:
    """
    If risk_flag is set, loop back to supervisor for re-evaluation.
    Guard: only loop once (risk_flag is reset by supervisor, so this won't loop forever).
    """
    if state.get("risk_flag"):
        return "supervisor"
    return "final_decision"
