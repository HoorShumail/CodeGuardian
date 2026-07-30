SYSTEM_PROMPT = """You are an expert code reviewer acting as **{personality}**.

Your specific focus area:
{focus_area}

General instructions:
- Produce a thorough, actionable review based on your assigned personality.
- Focus on: Logic, Security, Performance, and Maintainability.
- Suggest concrete fixes.
- Do not be overly pedantic about minor style preferences unless it fits your personality.
"""

TONE_CONFIGS = {
    "The Architect": {
        "personality": "a Senior Software Architect",
        "focus_area": "Focus on high-level design patterns, scalability, system boundaries, and long-term maintainability. Look for 'code smells' that indicate architectural debt."
    },
    "The Security Auditor": {
        "personality": "a specialized Security Engineer",
        "focus_area": "Focus exclusively on potential vulnerabilities, injection risks, authentication flaws, data privacy, and improper error handling that could leak info."
    },
    "The Junior Mentor": {
        "personality": "a supportive Lead Developer / Mentor",
        "focus_area": "Focus on clean code, readability, and educational explanations. Explain WHY a change is needed so the developer learns from the feedback."
    }
}


def build_system_prompt(tone: str = "The Architect") -> str:
    config = TONE_CONFIGS.get(tone, TONE_CONFIGS["The Architect"])
    return SYSTEM_PROMPT.format(
        personality=config["personality"],
        focus_area=config["focus_area"]
    )


def build_user_prompt(state: dict) -> str:
    tool_context = []

    if state.get("lint_results"):
        tool_context.append("=== LINTER OUTPUT (ruff) ===")
        for item in state["lint_results"]:
            tool_context.append(
                f"{item.get('filename')}:{item.get('location', {}).get('row')} "
                f"[{item.get('code')}] {item.get('message')}"
            )

    if state.get("security_results"):
        tool_context.append("\n=== SECURITY SCAN (bandit) ===")
        for item in state["security_results"]:
            tool_context.append(
                f"{item.get('filename')}:{item.get('line_number')} "
                f"[{item.get('test_id')}] {item.get('issue_text')} "
                f"(severity: {item.get('issue_severity')})"
            )

    if state.get("complexity_results"):
        tool_context.append("\n=== COMPLEXITY REPORT (radon) ===")
        for item in state["complexity_results"]:
            tool_context.append(str(item))

    tool_section = "\n".join(tool_context) if tool_context else "No tool results available."

    return f"""Please review the following pull request diff.

=== DIFF ===
{state.get('diff', '')}

=== STATIC ANALYSIS RESULTS ===
{tool_section}

Produce a structured review with inline comments, an overall summary, a quality score (0-100), and whether this PR should be approved.
"""