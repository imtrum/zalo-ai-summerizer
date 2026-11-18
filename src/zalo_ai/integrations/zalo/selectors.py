"""Shared selector values for Zalo Web and its diagnostics."""
CONVERSATION_SELECTOR = ".msg-item"
CONVERSATION_NAME_SELECTOR = ".conv-item-title__name"
CONVERSATION_ID_ATTRIBUTE = "anim-data-id"
CONVERSATION_DATA_ID_ATTRIBUTE = "data-id"
CONVERSATION_SCROLL_CONTAINER_SELECTOR = (
    ".ReactVirtualized__Grid__innerScrollContainer"
)
MESSAGE_FRAME_SELECTOR = '[data-component="message-content-view"]'
MESSAGE_TEXT_SELECTOR = '[data-component="message-text-content"]'
MESSAGE_SENDER_SELECTOR = ".message-sender-name-content"
MESSAGE_TIME_SELECTOR = ".card-send-time__sendTime, .card-send-time"
SCROLL_CONTAINER_SELECTOR = CONVERSATION_SCROLL_CONTAINER_SELECTOR
FRAME_SELECTOR = MESSAGE_FRAME_SELECTOR
TEXT_SELECTOR = MESSAGE_TEXT_SELECTOR
SENDER_SELECTOR = MESSAGE_SENDER_SELECTOR
TIME_SELECTOR = MESSAGE_TIME_SELECTOR
CONVERSATION_SELECTORS = {
    "name_selector": CONVERSATION_NAME_SELECTOR,
    "id_attribute": CONVERSATION_ID_ATTRIBUTE,
    "data_id_attribute": CONVERSATION_DATA_ID_ATTRIBUTE,
}
