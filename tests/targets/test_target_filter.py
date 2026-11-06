
from datetime import datetime

from zalo_ai.models.message import Message
from zalo_ai.targets.filter import filter_messages_by_target_ids


def test_filter_messages_by_target_ids():
    messages = [
        Message(
            message_id="msg_001",
            target_id="group_001",
            sender="Alice",
            content="Project meeting tomorrow.",
            timestamp=datetime(2026, 10, 12, 8, 0),
        ),
        Message(
            message_id="msg_002",
            target_id="group_002",
            sender="Bob",
            content="Lunch at noon.",
            timestamp=datetime(2026, 10, 12, 8, 5),
        ),
    ]

    result = filter_messages_by_target_ids(
        messages,
        {"group_001"},
    )

    assert len(result) == 1
    assert result[0].message_id == "msg_001"


def test_filter_messages_returns_empty_list_when_no_targets_match():
    messages = [
        Message(
            message_id="msg_001",
            target_id="group_001",
            sender="Alice",
            content="Hello",
            timestamp=datetime(2026, 10, 12, 8, 0),
        ),
    ]

    result = filter_messages_by_target_ids(messages, {"group_999"})

    assert result == []