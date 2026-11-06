
from datetime import datetime

from zalo_ai.models.message import Message


def test_message_creation():
    message = Message(
        message_id="msg_001",
        target_id="example_group_001",
        sender="Alice",
        content="The meeting starts at 9 AM.",
        timestamp=datetime(2026, 10, 9, 9, 0),
    )

    assert message.message_id == "msg_001"
    assert message.target_id == "example_group_001"
    assert message.sender == "Alice"
    assert message.content == "The meeting starts at 9 AM."
    assert message.timestamp == datetime(2026, 10, 9, 9, 0)