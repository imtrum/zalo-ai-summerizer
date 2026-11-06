from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
BROWSER_PROFILE = DATA_DIR / "browser_profile"
TARGETS_FILE = DATA_DIR / "targets.json"
SUMMARIZATION_PROMPT_FILE = DATA_DIR / "summarization_prompt.txt"
LOG_DIR = PROJECT_ROOT / "logs"
SAMPLE_MESSAGES_FILE = PROJECT_ROOT / "tests" / "fixtures" / "sample_messages.json"
