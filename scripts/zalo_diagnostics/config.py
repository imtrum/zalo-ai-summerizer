from zalo_ai.config.timezone import VN_TZ
from zalo_ai.integrations.zalo.selectors import (
    CONVERSATION_DATA_ID_ATTRIBUTE,
    CONVERSATION_ID_ATTRIBUTE,
    CONVERSATION_NAME_SELECTOR,
    CONVERSATION_SCROLL_CONTAINER_SELECTOR,
    CONVERSATION_SELECTOR,
    FRAME_SELECTOR,
    SENDER_SELECTOR,
    TEXT_SELECTOR,
    TIME_SELECTOR,
)
from zalo_ai.paths import BROWSER_PROFILE, PROJECT_ROOT

# Selectors are exploratory observations and should be rechecked against Zalo.
SELECTORS = {
    "frame": FRAME_SELECTOR,
    "text": TEXT_SELECTOR,
    "sender": SENDER_SELECTOR,
    "time": TIME_SELECTOR,
    "conversation": CONVERSATION_SELECTOR,
    "conversation_name": CONVERSATION_NAME_SELECTOR,
    "conversation_id_attribute": CONVERSATION_ID_ATTRIBUTE,
    "conversation_data_id_attribute": CONVERSATION_DATA_ID_ATTRIBUTE,
    "conversation_scroll_container": CONVERSATION_SCROLL_CONTAINER_SELECTOR,
}

MISSING = "<THIẾU>"
MAX_SCROLL_ROUNDS = 6
SCROLL_WAIT_MS = 1500
