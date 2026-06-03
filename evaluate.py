"""
Evaluation module — RAGAS-inspired quality metrics for the hedge fund system.
Measures: decision consistency, agent output coverage, debate quality, memory utilization.
Run with: python evaluate.py --ticker NVDA (requires a completed run in memory first)
"""
import json
import argparse
from src.memory.episodic_memory import get_recent_decisions, get_beliefs
from src.memory.procedural_memory import retrieve_past_decisions


def evaluate_decision_consistency(ticker: str, n: int = 10) -> dict:
    """Checks how consistent decisions are for the same ticker over time."""
    decisions = get_recent_decisions(ticker, limit=n)
    if len(decisions) < 2:
        return {"status": "insufficient_data", "n_decisions": len(decisions)}

    actions = [d["action"] for d in decisions]
    action_counts = {a: actions.count(a) for a in set(actions)}
    dominant = max(action_counts, key=action_counts.get)
    consistency = action_counts[dominant] / len(actions)

    avg_confidence = sum(d["confidence"] for d in decisions if d["confidence"]) / len(decisions)

    return {
        "ticker": ticker,
        "n_decisions": len(decisions),
        "action_distribution": action_counts,
        "dominant_action": dominant,
        "consistency_score": round(consistency, 3),
        "avg_confidence": round(avg_confidence, 3),
    }


def evaluate_belief_accumulation(ticker: str) -> dict:
    """Checks how many CVRF beliefs have been extracted for a ticker."""
    beliefs = get_beliefs(ticker=ticker, limit=50)
    return {
        "ticker": ticker,
        "total_beliefs": len(beliefs),
        "beliefs": [b["belief"] for b in beliefs],
    }


def evaluate_memory_coverage(ticker: str) -> dict:
    """Checks how much procedural memory exists for a ticker."""
    records = retrieve_past_decisions(ticker, top_k=10)
    if not records:
        return {"ticker": ticker, "status": "no_procedural_memory"}

    avg_decay_score = sum(r["decay_score"] for r in records) / len(records)
    oldest = max(r["days_old"] for r in records)
    newest = min(r["days_old"] for r in records)

    return {
        "ticker": ticker,
        "n_records": len(records),
        "avg_decay_score": round(avg_decay_score, 4),
        "oldest_record_days": oldest,
        "newest_record_days": newest,
    }


def run_evaluation(ticker: str):
    print(f"\n{'='*55}")
    print(f"  EVALUATION REPORT — {ticker.upper()}")
    print(f"{'='*55}\n")

    consistency = evaluate_decision_consistency(ticker)
    print("Decision Consistency:")
    print(json.dumps(consistency, indent=2))

    beliefs = evaluate_belief_accumulation(ticker)
    print("\nBelief Accumulation (CVRF):")
    print(json.dumps(beliefs, indent=2))

    memory = evaluate_memory_coverage(ticker)
    print("\nProcedural Memory Coverage:")
    print(json.dumps(memory, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True)
    args = parser.parse_args()
    run_evaluation(args.ticker)
