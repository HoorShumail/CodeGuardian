from langgraph.types import interrupt
from src.state import ReviewState


def hitl_review(state: ReviewState) -> dict:
    """
    Human-in-the-loop node. Execution pauses HERE.
    LangGraph checkpoints the full state to SQLite.
    The process can be resumed later with Command(resume=<feedback>).

    Expected feedback values:
      - "approve"              → proceed to output_report
      - "revise: <your notes>" → loop back to ai_analysis with the notes injected
    """
    comments_preview = "\n".join(
        f"  [{c.severity.upper()}] {c.file}:{c.line} — {c.message}"
        for c in state.get("ai_comments", [])
    )

    feedback = interrupt({
        "score": state.get("score"),
        "approved": state.get("approved"),
        "summary": state.get("overall_summary"),
        "comments_preview": comments_preview,
        "instruction": (
            "Reply 'approve' to accept the review and generate the report, "
            "or 'revise: <your notes>' to send additional context back to the AI."
        ),
    })

    return {"human_feedback": feedback}


def should_reanalyze(state: ReviewState) -> str:
    """
    Conditional edge function called after hitl_review.
    Routes to ai_analysis if human asked for a revision, otherwise to output_report.
    """
    feedback = state.get("human_feedback", "")
    if isinstance(feedback, str) and feedback.strip().lower().startswith("revise"):
        return "ai_analysis"
    return "output_report"