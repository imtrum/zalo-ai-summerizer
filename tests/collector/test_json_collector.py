
import json
from datetime import datetime

import pytest

from zalo_ai.collector.message_collector import JsonMessageCollector


def test_collect_messages_loads_json(tmp_path):
    data = [
        {
            "message_id": "msg_001",
            "target_id": "group_001",
            "sender": "Alice",
            "content": "Meeting at 9 AM.",
            "timestamp": "2026-10-11T08:00:00",
        }
    ]

    file_path = tmp_path / "messages.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    collector = JsonMessageCollector(file_path)
    messages = collector.collect_messages()

    assert len(messages) == 1
    assert messages[0].message_id == "msg_001"
    assert messages[0].target_id == "group_001"
    assert messages[0].sender == "Alice"
    assert messages[0].content == "Meeting at 9 AM."
    assert messages[0].timestamp == datetime(2026, 10, 11, 8, 0)


def test_collect_messages_rejects_non_list_json(tmp_path):
    file_path = tmp_path / "messages.json"
    file_path.write_text(
        '{"message_id": "msg_001"}',
        encoding="utf-8",
    )

    collector = JsonMessageCollector(file_path)

    with pytest.raises(ValueError, match="must contain a list"):
        collector.collect_messages()


def test_collect_messages_rejects_invalid_json(tmp_path):
    file_path = tmp_path / "messages.json"
    file_path.write_text("{invalid json}", encoding="utf-8")

    collector = JsonMessageCollector(file_path)

    with pytest.raises(json.JSONDecodeError):
        collector.collect_messages()



def test_collect_messages_rejects_non_object_record(tmp_path):
    import json
    import pytest

    from zalo_ai.collector.message_collector import JsonMessageCollector

    file_path = tmp_path / "messages.json"
    file_path.write_text(json.dumps(["not a message object"]), encoding="utf-8")

    collector = JsonMessageCollector(file_path)

    with pytest.raises(ValueError, match="must be a JSON object"):
        collector.collect_messages()


def test_collect_messages_rejects_invalid_timestamp(tmp_path):
    import json
    import pytest

    from zalo_ai.collector.message_collector import JsonMessageCollector

    record = {
        "message_id": "msg_001",
        "target_id": "group_001",
        "sender": "Alice",
        "content": "Hello",
        "timestamp": "not-a-timestamp",
    }

    file_path = tmp_path / "messages.json"
    file_path.write_text(json.dumps([record]), encoding="utf-8")

    collector = JsonMessageCollector(file_path)

    with pytest.raises(ValueError, match="Invalid message at index 0"):
        collector.collect_messages()