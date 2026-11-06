import os

from dotenv import load_dotenv

from zalo_ai.paths import PROJECT_ROOT


load_dotenv(dotenv_path=PROJECT_ROOT / ".env")


AI_PROVIDER = os.getenv("AI_PROVIDER", "")
AI_MODEL = os.getenv("AI_MODEL", "")
AI_FALLBACK_MODELS = tuple(
    model.strip()
    for model in os.getenv(
        "AI_FALLBACK_MODELS",
        "gemini-2.5-flash-lite",
    ).split(",")
    if model.strip()
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.2"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))

SUMMARY_LANGUAGE = os.getenv("SUMMARY_LANGUAGE", "vi")
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "100"))

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "json")
