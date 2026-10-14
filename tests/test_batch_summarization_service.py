from datetime import datetime
from unittest.mock import MagicMock

from zalo_ai.models.message import Message
from zalo_ai.summarizer.batch_summarization_service import (
    BatchSummarizationService,
)


def test_summarize_messages_returns_one_summary_per_target():
    messages = [
        Message(
            message_id="msg_001",
            target_id="group_001",
            sender="Alice",
            content="Meeting at 9 AM.",
            timestamp=datetime(2026, 10, 11, 8, 0),
        ),
        Message(
            message_id="msg_002",
            target_id="group_002",
            sender="Bob",
            content="Submit the report today.",
            timestamp=datetime(2026, 10, 11, 8, 5),
        ),
    ]

    mock_service = MagicMock()
    mock_service.summarize.side_effect = [
        "Meeting at 9 AM.",
        "Submit the report today.",
    ]

    service = BatchSummarizationService(
        summarization_service=mock_service
    )

    result = service.summarize_messages(messages)

    assert result == {
        "group_001": "Meeting at 9 AM.",
        "group_002": "Submit the report today.",
    }
    assert mock_service.summarize.call_count == 2


def test_summarize_messages_returns_empty_dict_for_no_messages():
    mock_service = MagicMock()
    service = BatchSummarizationService(
        summarization_service=mock_service
    )

    result = service.summarize_messages([])

    assert result == {}
    mock_service.summarize.assert_not_called()