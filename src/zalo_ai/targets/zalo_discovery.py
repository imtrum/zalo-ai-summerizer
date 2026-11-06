"""Compatibility exports for Zalo conversation discovery."""
from zalo_ai.integrations.zalo.conversations import (
    discover_conversations,
    get_visible_conversation_ids,
    open_visible_conversation,
)
from zalo_ai.integrations.zalo.selectors import (
    CONVERSATION_NAME_SELECTOR,
    CONVERSATION_SELECTOR,
    SCROLL_CONTAINER_SELECTOR,
)

__all__ = [
    "CONVERSATION_NAME_SELECTOR",
    "CONVERSATION_SELECTOR",
    "SCROLL_CONTAINER_SELECTOR",
    "discover_conversations",
    "get_visible_conversation_ids",
    "open_visible_conversation",
]
