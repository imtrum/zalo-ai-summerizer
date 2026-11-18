from zalo_ai.paths import PROJECT_ROOT, SUMMARIZATION_PROMPT_FILE


PROMPT_FILE = SUMMARIZATION_PROMPT_FILE

DEFAULT_PROMPT = (
    "Summarize the following conversation in Vietnamese.\n"
    "Preserve important information, decisions, tasks, and deadlines.\n"
    "Do not invent information that is not present in the messages."
)


def load_prompt() -> str:
    """Return the saved prompt, or the built-in default if none is saved."""
    try:
        prompt = PROMPT_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return DEFAULT_PROMPT

    return prompt or DEFAULT_PROMPT


def save_prompt(prompt: str) -> None:
    """Save non-empty prompt instructions for later summaries."""
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Prompt must not be empty.")

    PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROMPT_FILE.write_text(
        prompt.strip() + "\n",
        encoding="utf-8",
    )
