from datetime import timedelta, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BROWSER_PROFILE = PROJECT_ROOT / "data" / "browser_profile"

# Selectors are exploratory observations and should be rechecked against Zalo.
SELECTORS = {
    "frame": '[data-component="message-content-view"]',
    "text": '[data-component="message-text-content"]',
    "sender": ".message-sender-name-content",
    "time": ".card-send-time__sendTime, .card-send-time",
}

MISSING = "<THIẾU>"
MAX_SCROLL_ROUNDS = 6
SCROLL_WAIT_MS = 1500
VN_TZ = timezone(timedelta(hours=7))
