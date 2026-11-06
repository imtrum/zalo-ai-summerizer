
from datetime import datetime

from zalo_ai.models.message import Message
from zalo_ai.summarizer.message_batcher import create_batches


def make_message(message_id: str, target_id: str) -> Message:
    return Message(
        message_id=message_id,
        target_id=target_id,
        sender="user_001",
        content=f"Message {message_id}",
        timestamp=datetime(2026, 10, 10, 10, 0, 0),
    )


def test_create_batches_groups_messages_by_target():
    messages = [
        make_message("msg_001", "group_001"),
        make_message("msg_002", "group_002"),
        make_message("msg_003", "group_001"),
    ]

    batches = create_batches(messages)

    assert len(batches) == 2
    assert batches[0].target_id == "group_001"
    assert batches[0].get_message_count() == 2
    assert batches[1].target_id == "group_002"
    assert batches[1].get_message_count() == 1


def test_create_batches_with_no_messages():
    assert create_batches([]) == []


def test_create_batches_preserves_message_order():
    messages = [
        make_message("msg_001", "group_001"),
        make_message("msg_002", "group_001"),
        make_message("msg_003", "group_001"),
    ]

    batches = create_batches(messages)

    assert [
        message.message_id for message in batches[0].get_messages()
    ] == ["msg_001", "msg_002", "msg_003"]