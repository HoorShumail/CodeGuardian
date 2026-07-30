from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
CHECKPOINT_DB_PATH = os.getenv("CHECKPOINT_DB_PATH", "checkpoints/review.db")

# Tool binary paths (assumes same virtualenv)
RUFF_PATH = "ruff"
BANDIT_PATH = "bandit"
RADON_PATH = "radon"

# How many context lines to include around each changed hunk
DIFF_CONTEXT_LINES = 5