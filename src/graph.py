from langgraph.graph import StateGraph, END, START
from langgraph.types import Send
from langgraph.checkpoint.sqlite import SqliteSaver

from src.state import ReviewState
from src.nodes import (
    fetch_diff,
    parse_files,
    run_linter,
    run_security,
    check_complexity,
    ai_analysis,
    hitl_review,
    should_reanalyze,
    output_report,
)
from config import CHECKPOINT_DB_PATH


def dispatch_tools(state: ReviewState) -> list[Send]:
    """
    Fan-out node: dispatches all three tool checks in parallel using Send API.
    Each Send targets a different node with the same current state.
    LangGraph runs them concurrently and merges results via the Annotated[list, add] reducer.
    """
    return [
        Send("run_linter", state),
        Send("run_security", state),
        Send("check_complexity", state),
    ]


def build_graph():
    builder = StateGraph(ReviewState)

    # ── Register all nodes ──────────────────────────────────────────────
    builder.add_node("fetch_diff", fetch_diff)
    builder.add_node("parse_files", parse_files)
    builder.add_node("run_linter", run_linter)
    builder.add_node("run_security", run_security)
    builder.add_node("check_complexity", check_complexity)
    builder.add_node("ai_analysis", ai_analysis)
    builder.add_node("hitl_review", hitl_review)
    builder.add_node("output_report", output_report)

    # ── Linear edges ────────────────────────────────────────────────────
    builder.add_edge(START, "fetch_diff")
    builder.add_edge("fetch_diff", "parse_files")

    # ── Fan-out: parse_files → 3 tool nodes in parallel ─────────────────
    builder.add_conditional_edges("parse_files", dispatch_tools)

    # ── Fan-in: all tool nodes → ai_analysis ────────────────────────────
    builder.add_edge("run_linter", "ai_analysis")
    builder.add_edge("run_security", "ai_analysis")
    builder.add_edge("check_complexity", "ai_analysis")

    # ── HITL interrupt ───────────────────────────────────────────────────
    builder.add_edge("ai_analysis", "hitl_review")

    # ── Conditional: approve → output_report | revise → ai_analysis ─────
    builder.add_conditional_edges(
        "hitl_review",
        should_reanalyze,
        {
            "ai_analysis": "ai_analysis",
            "output_report": "output_report",
        },
    )

    builder.add_edge("output_report", END)

    # ── Compile with SQLite checkpointer for persistence ─────────────────
    import sqlite3
    conn = sqlite3.connect(CHECKPOINT_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["hitl_review"],  # pause before HITL node
    )


graph = build_graph()