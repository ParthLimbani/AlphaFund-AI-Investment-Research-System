"""
LangGraph workflow — 8-node graph.

Flow:
  supervisor
    → [fundamental | technical | sentiment]  (parallel)
    → synthesizer
    → debate
    → risk_manager  (conditional: risk_flag → supervisor)
    → final_decision
    → reflection
    → END
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.graph.state import HedgeFundState
from src.graph.routing import route_after_risk

from src.agents.supervisor import supervisor_node
from src.agents.fundamental import fundamental_node
from src.agents.technical import technical_node
from src.agents.sentiment import sentiment_node
from src.agents.synthesizer import synthesizer_node
from src.agents.debate import debate_node
from src.agents.risk_manager import risk_manager_node
from src.agents.final_decision import final_decision_node
from src.agents.reflection import reflection_node


def build_graph(checkpointer=None):
    builder = StateGraph(HedgeFundState)

    builder.add_node("supervisor",     supervisor_node)
    builder.add_node("fundamental",    fundamental_node)
    builder.add_node("technical",      technical_node)
    builder.add_node("sentiment",      sentiment_node)
    builder.add_node("synthesizer",    synthesizer_node)
    builder.add_node("debate",         debate_node)
    builder.add_node("risk_manager",   risk_manager_node)
    builder.add_node("final_decision", final_decision_node)
    builder.add_node("reflection",     reflection_node)

    builder.set_entry_point("supervisor")

    # supervisor → parallel research
    builder.add_edge("supervisor",  "fundamental")
    builder.add_edge("supervisor",  "technical")
    builder.add_edge("supervisor",  "sentiment")

    # parallel research → synthesizer (fan-in)
    builder.add_edge("fundamental", "synthesizer")
    builder.add_edge("technical",   "synthesizer")
    builder.add_edge("sentiment",   "synthesizer")

    # synthesizer → debate → risk
    builder.add_edge("synthesizer", "debate")
    builder.add_edge("debate",      "risk_manager")

    # risk_manager → conditional (risk_flag loops back to supervisor)
    builder.add_conditional_edges(
        "risk_manager",
        route_after_risk,
        {"supervisor": "supervisor", "final_decision": "final_decision"},
    )

    builder.add_edge("final_decision", "reflection")
    builder.add_edge("reflection",     END)

    return builder.compile(checkpointer=checkpointer)


def get_graph():
    return build_graph(checkpointer=MemorySaver())
