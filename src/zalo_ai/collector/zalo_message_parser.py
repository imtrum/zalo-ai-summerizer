"""Compatibility exports for the Zalo message parser."""
from zalo_ai.integrations.zalo.messages.parser import (
    COLLECT_JS,
    FRAME_SELECTOR,
    SENDER_SELECTOR,
    TEXT_SELECTOR,
    TIME_SELECTOR,
    VN_TZ,
    clean_text,
    parse_date,
    parse_timestamp,
)

__all__ = [
    "COLLECT_JS",
    "FRAME_SELECTOR",
    "SENDER_SELECTOR",
    "TEXT_SELECTOR",
    "TIME_SELECTOR",
    "VN_TZ",
    "clean_text",
    "parse_date",
    "parse_timestamp",
]
