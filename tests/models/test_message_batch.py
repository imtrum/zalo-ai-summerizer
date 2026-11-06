
from datetime import datetime

from zalo_ai.models.message import Message
from zalo_ai.models.message_batch import MessageBatch


def test_message_batch():
    message1 = Message(
        message_id="msg_001",
        target_id="group_001",
        sender="Alice",
        content="Hello!",
        timestamp=datetime(2026, 10, 9, 9, 0),
    )

    message2 = Message(
        message_id="msg_002",
        target_id="group_001",
        sender="Bob",
        content="Hi!",
        timestamp=datetime(2026, 10, 9, 9, 1),
    )

    batch = MessageBatch(
        target_id="group_001",
        messages=[message1, message2],
    )

    assert batch.target_id == "group_001"
    assert batch.get_message_count() == 2
    assert batch.get_messages() == [message1, message2]



import pytest


def test_message_batch_rejects_mismatched_target():
    message = Message(
        message_id="msg_001",
        target_id="group_002",
        sender="Alice",
        content="Hello!",
        timestamp=datetime(2026, 10, 10, 9, 0),
    )

    with pytest.raises(ValueError, match="belongs to target"):
        MessageBatch(
            target_id="group_001",
            messages=[message],
        )


def test_message_batch_rejects_empty_target_id():
    with pytest.raises(ValueError, match="target_id cannot be empty"):
        MessageBatch(
            target_id="",
            messages=[],
        )