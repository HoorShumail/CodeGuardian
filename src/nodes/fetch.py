from src.state import ReviewState
from config import GITHUB_TOKEN
from github import Github
import re


def fetch_diff(state: ReviewState) -> dict:
    """
    Fetch the raw unified diff from either a GitHub PR URL or a local .patch file.
    Returns only the 'diff' key to update state.
    """
    pr_url = state.get("pr_url", "").strip()
    local_path = state.get("local_diff_path", "").strip()
    pasted_code = state.get("pasted_code", "").strip()
    pasted_filename = state.get("pasted_filename", "snippet.py").strip()

    if pr_url:
        diff = _fetch_from_github(pr_url)
    elif local_path:
        diff = _fetch_from_local(local_path)
    elif pasted_code:
        diff = _fetch_from_pasted(pasted_code, pasted_filename)
    else:
        raise ValueError("Provide 'pr_url', 'local_diff_path', or 'pasted_code' in initial state.")

    return {"diff": diff}


def _fetch_from_github(pr_url: str) -> str:
    """
    Parse a GitHub PR URL and fetch the diff via PyGithub.
    Expected format: https://github.com/{owner}/{repo}/pull/{number}
    """
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, pr_url)
    if not match:
        raise ValueError(f"Could not parse GitHub PR URL: {pr_url}")

    owner, repo_name, pr_number = match.group(1), match.group(2), int(match.group(3))

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(f"{owner}/{repo_name}")
    pr = repo.get_pull(pr_number)

    # PyGithub doesn't expose raw diff directly — use the comparison
    comparison = repo.compare(pr.base.sha, pr.head.sha)
    diff_lines = []

    for file in comparison.files:
        if file.patch:
            diff_lines.append(f"--- a/{file.filename}")
            diff_lines.append(f"+++ b/{file.filename}")
            diff_lines.append(file.patch)

    return "\n".join(diff_lines)


def _fetch_from_local(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _fetch_from_pasted(code: str, filename: str) -> str:
    """
    Convert a raw block of code into a 'synthetic' unified diff
    where everything is an addition.
    """
    lines = code.splitlines()
    line_count = len(lines)
    
    diff_lines = [
        f"--- a/{filename}",
        f"+++ b/{filename}",
        f"@@ -0,0 +1,{line_count} @@",
    ]
    
    for line in lines:
        diff_lines.append(f"+{line}")
        
    return "\n".join(diff_lines)