import subprocess
import json
import tempfile
import os
from src.state import ReviewState
from config import RUFF_PATH, BANDIT_PATH, RADON_PATH


# ─────────────────────────────────────────────
# Helper: write changed Python files to a temp dir so tools can run on them
# ─────────────────────────────────────────────

def _write_temp_files(state: ReviewState) -> tuple[str, list[str]]:
    """
    Write the added/modified lines from the diff into a temp directory.
    Returns (tmpdir_path, list_of_filepaths).
    Only writes Python files — other languages skip tool nodes gracefully.
    """
    tmpdir = tempfile.mkdtemp(prefix="cr_agent_")
    written = []

    for file_info in state.get("files", []):
        if file_info["language"] != "python":
            continue

        filename = file_info["filename"]
        filepath = os.path.join(tmpdir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Collect only added lines (strip the leading "+")
        added_lines = []
        for hunk in file_info.get("hunks", []):
            for line in hunk.get("lines", []):
                if line.startswith("+"):
                    added_lines.append(line[1:])
                elif line.startswith(" "):
                    added_lines.append(line[1:])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(added_lines))

        written.append(filepath)

    return tmpdir, written


# ─────────────────────────────────────────────
# Node: run_linter
# ─────────────────────────────────────────────

def run_linter(state: ReviewState) -> dict:
    """
    Run ruff linter on changed Python files.
    Returns lint_results as a list of issue dicts.
    """
    tmpdir, filepaths = _write_temp_files(state)

    if not filepaths:
        return {"lint_results": []}

    try:
        result = subprocess.run(
            [RUFF_PATH, "check", "--output-format=json"] + filepaths,
            capture_output=True,
            text=True,
            timeout=30,
        )
        issues = json.loads(result.stdout) if result.stdout.strip() else []
    except Exception as e:
        issues = [{"error": str(e)}]

    return {"lint_results": issues}


# ─────────────────────────────────────────────
# Node: run_security
# ─────────────────────────────────────────────

def run_security(state: ReviewState) -> dict:
    """
    Run bandit security scanner on changed Python files.
    Returns security_results as a list of issue dicts.
    """
    tmpdir, filepaths = _write_temp_files(state)

    if not filepaths:
        return {"security_results": []}

    try:
        result = subprocess.run(
            [BANDIT_PATH, "-f", "json", "-q"] + filepaths,
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout) if result.stdout.strip() else {}
        issues = data.get("results", [])
    except Exception as e:
        issues = [{"error": str(e)}]

    return {"security_results": issues}


# ─────────────────────────────────────────────
# Node: check_complexity
# ─────────────────────────────────────────────

def check_complexity(state: ReviewState) -> dict:
    """
    Run radon cyclomatic complexity check on changed Python files.
    Flags functions with complexity grade C or worse (score >= 7).
    Returns complexity_results as a list of dicts.
    """
    tmpdir, filepaths = _write_temp_files(state)

    if not filepaths:
        return {"complexity_results": []}

    try:
        result = subprocess.run(
            [RADON_PATH, "cc", "--json", "--min", "C"] + filepaths,
            capture_output=True,
            text=True,
            timeout=30,
        )
        data = json.loads(result.stdout) if result.stdout.strip() else {}

        issues = []
        for filepath, functions in data.items():
            for fn in functions:
                issues.append({
                    "file": filepath,
                    "function": fn.get("name"),
                    "complexity": fn.get("complexity"),
                    "rank": fn.get("rank"),
                    "lineno": fn.get("lineno"),
                })
    except Exception as e:
        issues = [{"error": str(e)}]

    return {"complexity_results": issues}