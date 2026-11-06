"""Compatibility export for the Zalo message collector."""
from zalo_ai.integrations.zalo.messages.collector import (
    MAX_SCROLL_ROUNDS,
    SCROLL_WAIT_MS,
    VN_TZ,
    ZaloMessageCollector,
)

__all__ = [
    "MAX_SCROLL_ROUNDS",
    "SCROLL_WAIT_MS",
    "VN_TZ",
    "ZaloMessageCollector",
]
