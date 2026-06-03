from typing import TypedDict, Annotated
import operator


class HedgeFundState(TypedDict):
    # --- Input ---
    ticker: str
    user_query: str

    # --- Memory context (injected by supervisor at graph start) ---
    past_decisions: list        # from procedural memory (ChromaDB), timeliness-decay ranked
    investment_beliefs: list    # from episodic memory (CVRF-extracted beliefs)

    # --- Research outputs ---
    fundamental_analysis: dict
    technical_analysis: dict
    sentiment_analysis: dict
    synthesized_research: dict

    # --- Debate (single combined node output) ---
    debate_result: dict         # bull_case, bear_case, rebuttals, winner, confidence, lean

    # --- Risk & decision ---
    risk_analysis: dict
    risk_flag: bool
    final_decision: dict

    # --- Reflection output ---
    new_beliefs: list

    # --- Error tracking ---
    agent_errors: Annotated[list, operator.add]
