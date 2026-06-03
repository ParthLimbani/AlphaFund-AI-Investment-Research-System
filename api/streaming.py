"""
SSE generator that wraps LangGraph's .stream() and emits structured events
for each node completion. Consumed by the /stream/{session_id} endpoint.
"""
import json
import asyncio
import uuid
import time
from typing import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor

# In-memory session store: session_id → full final state (set when done)
_sessions: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=4)

# Result cache: ticker → {session_id, ts}  — avoids re-running within TTL
_ticker_cache: dict[str, dict] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes

# Human-readable labels for each node
NODE_LABELS = {
    "supervisor":     "Supervisor",
    "fundamental":    "Fundamental Analyst",
    "technical":      "Technical Analyst",
    "sentiment":      "Sentiment Analyst",
    "synthesizer":    "Research Synthesizer",
    "debate":         "Bull vs Bear Debate",
    "risk_manager":   "Risk Manager",
    "final_decision": "Final Decision",
    "reflection":     "Memory & Reflection",
}

PARALLEL_GROUPS = [
    {"fundamental", "technical", "sentiment"},
]


def _extract_node_summary(node_name: str, node_output: dict) -> str:
    """Extracts a short human-readable summary from a node's output."""
    if node_name == "fundamental":
        fa = node_output.get("fundamental_analysis", {})
        return f"{fa.get('valuation_signal','?')} · {fa.get('growth_outlook','?')} growth"
    if node_name == "technical":
        ta = node_output.get("technical_analysis", {})
        return f"Trend: {ta.get('trend','?')} · Momentum: {ta.get('momentum','?')}"
    if node_name == "sentiment":
        sa = node_output.get("sentiment_analysis", {})
        return f"{sa.get('overall_sentiment','?')} · score {sa.get('sentiment_score','?')}"
    if node_name == "synthesizer":
        sr = node_output.get("synthesized_research", {})
        return f"Signal: {sr.get('overall_signal','?')} · {sr.get('signal_alignment','?')}"
    if node_name == "debate":
        dr = node_output.get("debate_result", {})
        return f"Winner: {dr.get('winner','?')} · {dr.get('investment_lean','?')} · confidence {dr.get('confidence','?')}"
    if node_name == "risk_manager":
        ra = node_output.get("risk_analysis", {})
        return f"Risk: {ra.get('risk_level','?')} · flag: {node_output.get('risk_flag', False)}"
    if node_name == "final_decision":
        fd = node_output.get("final_decision", {})
        return f"{fd.get('action','?')} · confidence {fd.get('confidence','?')}"
    if node_name == "reflection":
        beliefs = node_output.get("new_beliefs", [])
        return f"{len(beliefs)} new belief(s) extracted"
    return ""


def start_analysis(ticker: str, query: str = "") -> tuple[str, bool]:
    """
    Starts a LangGraph analysis run in a background thread.
    Returns (session_id, from_cache). If a fresh result exists for the ticker,
    returns the cached session immediately without re-running.
    """
    ticker = ticker.upper()
    cached = _ticker_cache.get(ticker)
    if cached and time.time() - cached["ts"] < CACHE_TTL_SECONDS:
        sid = cached["session_id"]
        if sid in _sessions and _sessions[sid]["status"] == "done":
            return sid, True

    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

    from src.graph.workflow import get_graph

    session_id = str(uuid.uuid4())
    _ticker_cache[ticker] = {"session_id": session_id, "ts": time.time()}
    _sessions[session_id] = {"status": "running", "ticker": ticker, "events": [], "final": None}

    initial_state = {
        "ticker": ticker.upper(),
        "user_query": query or f"Analyze {ticker.upper()} and provide an investment recommendation.",
        "past_decisions": [],
        "investment_beliefs": [],
        "fundamental_analysis": {},
        "technical_analysis": {},
        "sentiment_analysis": {},
        "synthesized_research": {},
        "debate_result": {},
        "risk_analysis": {},
        "risk_flag": False,
        "final_decision": {},
        "new_beliefs": [],
        "agent_errors": [],
    }

    def run():
        graph = get_graph()
        config = {"configurable": {"thread_id": session_id}}
        final_state = {}
        try:
            for step in graph.stream(initial_state, config=config, stream_mode="updates"):
                node_name = list(step.keys())[0]
                node_output = step[node_name]
                summary = _extract_node_summary(node_name, node_output)
                event = {
                    "node": node_name,
                    "label": NODE_LABELS.get(node_name, node_name),
                    "status": "complete",
                    "summary": summary,
                }
                _sessions[session_id]["events"].append(event)
                final_state.update(node_output)

            _sessions[session_id]["status"] = "done"
            _sessions[session_id]["final"] = final_state
        except Exception as e:
            _sessions[session_id]["status"] = "error"
            _sessions[session_id]["error"] = str(e)

    _executor.submit(run)
    return session_id, False


async def stream_events(session_id: str) -> AsyncGenerator[str, None]:
    """
    Async SSE generator. Polls the session's event buffer and yields
    new events as they arrive. Ends when status becomes 'done' or 'error'.
    """
    if session_id not in _sessions:
        yield f"data: {json.dumps({'error': 'session not found'})}\n\n"
        return

    sent_count = 0
    while True:
        session = _sessions[session_id]
        events = session["events"]

        # Yield any new events
        while sent_count < len(events):
            event = events[sent_count]
            yield f"data: {json.dumps(event)}\n\n"
            sent_count += 1

        status = session["status"]
        if status == "done":
            fd = (session.get("final") or {}).get("final_decision", {})
            done_event = {
                "node": "__done__",
                "status": "done",
                "action": fd.get("action", "HOLD"),
                "confidence": fd.get("confidence", 0),
            }
            yield f"data: {json.dumps(done_event)}\n\n"
            break
        elif status == "error":
            yield f"data: {json.dumps({'node': '__error__', 'error': session.get('error', 'unknown')})}\n\n"
            break

        await asyncio.sleep(0.3)


def get_result(session_id: str) -> dict | None:
    session = _sessions.get(session_id)
    if not session or session["status"] != "done":
        return None
    return session["final"]


def get_session_status(session_id: str) -> str:
    return _sessions.get(session_id, {}).get("status", "not_found")
