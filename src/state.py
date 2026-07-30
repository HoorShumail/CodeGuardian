from typing import TypedDict, Annotated
from operator import add
from src.schemas.review import ReviewComment


class ReviewState(TypedDict):
    # --- Input ---
    pr_url: str              # GitHub PR URL or empty if local
    local_diff_path: str     # Path to local .patch file if no PR URL
    pasted_code: str         # Direct raw code input
    pasted_filename: str     # Filename for pasted code (e.g. script.py)
    reviewer_tone: str       # Tone: Architect, Auditor, Mentor, etc.

    # --- Parsed data ---
    diff: str                # Raw unified diff string
    files: list[dict]        # List of {filename, hunks, language}

    # --- Tool results (Annotated with add so parallel nodes append safely) ---
    lint_results: Annotated[list[dict], add]
    security_results: Annotated[list[dict], add]
    complexity_results: Annotated[list[dict], add]

    # --- AI output ---
    ai_comments: list[ReviewComment]
    overall_summary: str
    score: int
    approved: bool

    # --- HITL ---
    human_feedback: str | None   # "approve" or "revise: <notes>"

    # --- Final ---
    final_report: str            # Markdown report string