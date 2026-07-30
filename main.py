"""
Code Review Agent — CLI entrypoint

Usage:
  # Review a GitHub PR
  python main.py --pr https://github.com/owner/repo/pull/42

  # Review a local diff file
  python main.py --diff path/to/changes.patch

  # Resume a paused review (after HITL interrupt)
  python main.py --resume <thread_id> --feedback "approve"
  python main.py --resume <thread_id> --feedback "revise: also check for missing null checks"
"""

import argparse
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from langgraph.types import Command

from src.graph import graph

console = Console()


def run_review(pr_url: str = "", local_diff_path: str = "") -> str:
    thread_id = str(uuid.uuid4())

    initial_state = {
        "pr_url": pr_url,
        "local_diff_path": local_diff_path,
        "lint_results": [],
        "security_results": [],
        "complexity_results": [],
        "ai_comments": [],
        "human_feedback": None,
        "final_report": "",
    }

    config = {"configurable": {"thread_id": thread_id}}

    console.print(Panel(f"[bold]Starting review[/bold]\nThread ID: [cyan]{thread_id}[/cyan]"))

    # Run graph — will pause at hitl_review due to interrupt_before
    for event in graph.stream(initial_state, config=config, stream_mode="values"):
        _print_progress(event)

    # After interrupt, show what the AI found
    state = graph.get_state(config)
    _print_ai_results(state.values)

    console.print(
        Panel(
            f"[yellow]Review paused for human approval.[/yellow]\n\n"
            f"To approve:\n  [green]python main.py --resume {thread_id} --feedback approve[/green]\n\n"
            f"To request revision:\n  [yellow]python main.py --resume {thread_id} --feedback \"revise: your notes here\"[/yellow]"
        )
    )

    return thread_id


def resume_review(thread_id: str, feedback: str):
    config = {"configurable": {"thread_id": thread_id}}

    console.print(Panel(f"[bold]Resuming review[/bold]\nThread: [cyan]{thread_id}[/cyan]\nFeedback: [yellow]{feedback}[/yellow]"))

    for event in graph.stream(
        Command(resume=feedback),
        config=config,
        stream_mode="values",
    ):
        _print_progress(event)

    console.print("[bold green]Review complete.[/bold green]")


def _print_progress(event: dict):
    # Show which node just completed based on what keys were updated
    if "diff" in event and event["diff"]:
        console.print("[dim][OK] Diff fetched[/dim]")
    if "files" in event and event["files"]:
        console.print(f"[dim][OK] Parsed {len(event['files'])} changed files[/dim]")
    if "lint_results" in event and event["lint_results"]:
        console.print(f"[dim][OK] Linter: {len(event['lint_results'])} issues[/dim]")
    if "security_results" in event and event["security_results"]:
        console.print(f"[dim][OK] Security: {len(event['security_results'])} issues[/dim]")
    if "ai_comments" in event and event["ai_comments"]:
        console.print(f"[dim][OK] AI analysis complete: {len(event['ai_comments'])} comments[/dim]")


def _print_ai_results(state: dict):
    table = Table(title="AI Review Summary", show_lines=True)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Score", str(state.get("score", "N/A")))
    table.add_row("Approved", "Yes" if state.get("approved") else "No")
    table.add_row("Comments", str(len(state.get("ai_comments", []))))
    table.add_row("Summary", state.get("overall_summary", "")[:200] + "...")

    console.print(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Code Review Agent")
    parser.add_argument("--pr", help="GitHub PR URL", default="")
    parser.add_argument("--diff", help="Local .patch file path", default="")
    parser.add_argument("--resume", help="Thread ID to resume", default="")
    parser.add_argument("--feedback", help="Human feedback for resume", default="approve")

    args = parser.parse_args()

    if args.resume:
        resume_review(args.resume, args.feedback)
    elif args.pr or args.diff:
        run_review(pr_url=args.pr, local_diff_path=args.diff)
    else:
        console.print("[red]Provide --pr, --diff, or --resume[/red]")
        parser.print_help()