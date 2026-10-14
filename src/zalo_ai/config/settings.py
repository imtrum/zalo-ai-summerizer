import os

from dotenv import load_dotenv


load_dotenv()


AI_PROVIDER = os.getenv("AI_PROVIDER", "")
AI_MODEL = os.getenv("AI_MODEL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.2"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))

SUMMARY_LANGUAGE = os.getenv("SUMMARY_LANGUAGE", "vi")
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "100"))

STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "json")

