from openai import OpenAI
from src.state import ReviewState
from src.schemas.review import ReviewOutput
from src.prompts.review import build_system_prompt, build_user_prompt
from config import MODEL_NAME, OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)


def ai_analysis(state: ReviewState) -> dict:
    """
    Core AI node. Sends the diff + tool results to GPT-4o and gets back
    a fully structured ReviewOutput (validated by Pydantic at the API level).

    Uses client.beta.chat.completions.parse() — OpenAI enforces the schema
    server-side so we never get malformed JSON or missing fields.
    """
    user_prompt = build_user_prompt(state)
    system_prompt = build_system_prompt(state.get("reviewer_tone", "The Architect"))

    response = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=ReviewOutput,
    )

    parsed: ReviewOutput = response.choices[0].message.parsed

    return {
        "ai_comments": parsed.comments,
        "overall_summary": parsed.overall_summary,
        "score": parsed.score,
        "approved": parsed.approved,
    }