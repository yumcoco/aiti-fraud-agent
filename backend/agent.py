from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from backend.models.transaction import Transaction
from backend.models.tool_outputs import GraphResult, ProfileResult, ScoreResult, SARReport
from backend.tools.graph_tool import investigate_transaction_network
from backend.tools.profile_tool import get_risk_profile
from backend.tools.scoring_tool import score_transaction
from backend.tools.report_tool import generate_sar_report
from backend.logger import get_logger


# ── State definition ──────────────────────────────────────────────
class AgentState(TypedDict):
    transaction:    Transaction
    trace_id:       str
    graph_result:   Optional[GraphResult]
    profile_result: Optional[ProfileResult]
    score_result:   Optional[ScoreResult]
    sar_report:     Optional[SARReport]


# ── Node functions ─────────────────────────────────────────────────
def node_graph(state: AgentState) -> AgentState:
    result = investigate_transaction_network(
        account_id=state["transaction"].account_id,
        trace_id=state["trace_id"]
    )
    return {**state, "graph_result": result}


def node_profile(state: AgentState) -> AgentState:
    result = get_risk_profile(
        account_id=state["transaction"].account_id,
        trace_id=state["trace_id"]
    )
    return {**state, "profile_result": result}


def node_score(state: AgentState) -> AgentState:
    result = score_transaction(
        tx=state["transaction"],
        graph=state["graph_result"],
        profile=state["profile_result"],
        trace_id=state["trace_id"]
    )
    return {**state, "score_result": result}


def node_report(state: AgentState) -> AgentState:
    result = generate_sar_report(
        tx=state["transaction"],
        graph=state["graph_result"],
        profile=state["profile_result"],
        score=state["score_result"],
        trace_id=state["trace_id"]
    )
    return {**state, "sar_report": result}


# ── Conditional edge ───────────────────────────────────────────────
def should_generate_report(state: AgentState) -> str:
    if state["score_result"] and state["score_result"].decision == "block":
        return "report"
    return "end"


# ── Build graph ────────────────────────────────────────────────────
def build_agent() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("graph_tool",   node_graph)
    graph.add_node("profile_tool", node_profile)
    graph.add_node("score_tool",   node_score)
    graph.add_node("report_tool",  node_report)

    graph.set_entry_point("graph_tool")
    graph.add_edge("graph_tool",   "profile_tool")
    graph.add_edge("profile_tool", "score_tool")
    graph.add_conditional_edges(
        "score_tool",
        should_generate_report,
        {"report": "report_tool", "end": END}
    )
    graph.add_edge("report_tool", END)

    return graph.compile()


# ── Public interface ───────────────────────────────────────────────
def run_agent(tx: Transaction, trace_id: str) -> AgentState:
    log = get_logger(trace_id)
    log.info("agent", status="start", account_id=tx.account_id)

    agent = build_agent()
    initial_state: AgentState = {
        "transaction":    tx,
        "trace_id":       trace_id,
        "graph_result":   None,
        "profile_result": None,
        "score_result":   None,
        "sar_report":     None,
    }

    result = agent.invoke(initial_state)
    log.info("agent",
             status="complete",
             decision=result["score_result"].decision if result["score_result"] else "unknown",
             account_id=tx.account_id)
    return result