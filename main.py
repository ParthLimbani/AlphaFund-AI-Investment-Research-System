"""
AI Hedge Fund — Main entrypoint.
Usage:
    python main.py --ticker NVDA
    python main.py --ticker AAPL --query "Is AAPL a good buy right now?"
    python main.py --ticker TSLA --verbose
"""
import argparse
import json
import uuid
from pprint import pprint

from src.graph.workflow import get_graph


def run_analysis(ticker: str, query: str = "", verbose: bool = False) -> dict:
    graph = get_graph()
    thread_id = str(uuid.uuid4())

    initial_state = {
        "ticker": ticker.upper(),
        "user_query": query or f"Analyze {ticker.upper()} and provide an investment recommendation.",
        "past_decisions": [],
        "investment_beliefs": [],
        "fundamental_analysis": {},
        "technical_analysis": {},
        "sentiment_analysis": {},
        "synthesized_research": {},
        "bull_case_round1": "",
        "bear_case_round1": "",
        "bull_rebuttal": "",
        "bear_rebuttal": "",
        "deliberation_bull": "",
        "deliberation_bear": "",
        "debate_rounds_done": 0,
        "debate_summary": {},
        "debate_ambiguous": False,
        "risk_analysis": {},
        "risk_flag": False,
        "final_decision": {},
        "new_beliefs": [],
        "agent_errors": [],
    }

    config = {"configurable": {"thread_id": thread_id}}

    print(f"\n{'='*60}")
    print(f"  AI HEDGE FUND — Analyzing {ticker.upper()}")
    print(f"{'='*60}\n")

    final_state = None
    step_count = 0
    for step in graph.stream(initial_state, config=config, stream_mode="updates"):
        step_count += 1
        node_name = list(step.keys())[0]
        print(f"[Step {step_count}] {node_name} ✓")

        if verbose:
            node_output = step[node_name]
            # Print non-empty non-verbose fields
            for k, v in node_output.items():
                if v and k not in ("past_decisions", "investment_beliefs"):
                    print(f"   {k}: {json.dumps(v, default=str)[:200]}")

        final_state = step

    # Extract final decision from last state
    # Re-invoke to get full final state
    result = graph.get_state(config)
    final = result.values if result else {}

    decision = final.get("final_decision", {})

    print(f"\n{'='*60}")
    print(f"  FINAL DECISION: {decision.get('action', 'N/A')}")
    print(f"  Confidence:     {decision.get('confidence', 'N/A')}")
    print(f"  Time Horizon:   {decision.get('time_horizon', 'N/A')}")
    print(f"  Price Target:   {decision.get('price_target', 'N/A')}")
    print(f"{'='*60}")
    print(f"\nExplanation:\n{decision.get('explanation', 'N/A')}")
    print(f"\nKey Reasons:")
    for r in decision.get("key_reasons", []):
        print(f"  • {r}")
    print(f"\nKey Risks:")
    for r in decision.get("key_risks", []):
        print(f"  • {r}")

    errors = final.get("agent_errors", [])
    if errors:
        print(f"\n[Warnings] Agent errors encountered:")
        for e in errors:
            print(f"  ! {e}")

    new_beliefs = final.get("new_beliefs", [])
    if new_beliefs:
        print(f"\n[Memory] New investment beliefs extracted:")
        for b in new_beliefs:
            print(f"  ★ {b}")

    print()
    return final


def main():
    parser = argparse.ArgumentParser(description="AI Hedge Fund — Multi-Agent Investment Analysis")
    parser.add_argument("--ticker", required=True, help="Stock ticker symbol (e.g. NVDA)")
    parser.add_argument("--query", default="", help="Custom analysis query (optional)")
    parser.add_argument("--verbose", action="store_true", help="Print intermediate agent outputs")
    args = parser.parse_args()

    run_analysis(ticker=args.ticker, query=args.query, verbose=args.verbose)


if __name__ == "__main__":
    main()
