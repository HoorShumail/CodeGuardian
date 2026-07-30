import os
from datetime import datetime
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from src.state import ReviewState
from config import MODEL_NAME, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)
console = Console()


def output_report(state: ReviewState) -> dict:
    """
    Final node. Generates a polished Markdown report using streaming
    so output appears progressively in the terminal via rich.

    Also saves the report to reports/<timestamp>.md
    """
    report_prompt = _build_report_prompt(state)

    console.print("\n[bold green]Generating final report...[/bold green]\n")

    report_chunks = []

    # Streaming call — tokens printed as they arrive
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a technical writer. Format the given review data into a clean, readable Markdown report.",
            },
            {"role": "user", "content": report_prompt},
        ],
        stream=True
    )

    for chunk in response:
        if chunk.choices[0].delta.content:
            token = chunk.choices[0].delta.content
            report_chunks.append(token)
            print(token, end="", flush=True)

    print()  # newline after streaming

    final_report = "".join(report_chunks)

    # Save to disk
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = f"reports/review_{timestamp}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(final_report)

    console.print(f"\n[bold]Report saved to:[/bold] {report_path}")

    return {"final_report": final_report}


def _build_report_prompt(state: ReviewState) -> str:
    comments_md = "\n".join(
        f"- **{c.severity.upper()}** `{c.file}:{c.line}` [{c.category}] — {c.message}"
        + (f"\n  > Fix: {c.suggested_fix}" if c.suggested_fix else "")
        for c in state.get("ai_comments", [])
    )

    return f"""
Create a Markdown code review report with the following data:

## Summary
{state.get("overall_summary", "N/A")}

## Score
{state.get("score", "N/A")} / 100

## Approved
{"Yes" if state.get("approved") else "No"}

## Inline Comments
{comments_md or "No comments."}

## Human Feedback Applied
{state.get("human_feedback") or "None (approved on first pass)"}

Format this into a professional, well-structured Markdown document suitable for sharing with the team.
"""