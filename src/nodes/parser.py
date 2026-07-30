import re
from src.state import ReviewState


# Map file extensions to language names
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c/cpp",
    ".rb": "ruby",
    ".sh": "bash",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
}


def parse_files(state: ReviewState) -> dict:
    """
    Parse the raw unified diff into a structured list of changed files with hunks.
    Each file entry: {filename, language, hunks: [{header, lines}]}
    """
    diff = state.get("diff", "")
    files = _parse_unified_diff(diff)
    return {"files": files}


def _parse_unified_diff(diff: str) -> list[dict]:
    files = []
    current_file = None
    current_hunk = None

    for line in diff.splitlines():
        # New file header
        if line.startswith("+++ b/"):
            filename = line[6:].strip()
            ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
            current_file = {
                "filename": filename,
                "language": LANGUAGE_MAP.get(ext, "unknown"),
                "hunks": [],
            }
            files.append(current_file)
            current_hunk = None

        # Hunk header e.g. @@ -10,7 +10,9 @@
        elif line.startswith("@@") and current_file is not None:
            current_hunk = {"header": line, "lines": []}
            current_file["hunks"].append(current_hunk)

        # Diff content lines
        elif current_hunk is not None and line and line[0] in ("+", "-", " "):
            current_hunk["lines"].append(line)

    return files