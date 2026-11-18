from datetime import datetime
from unittest.mock import MagicMock

import pytest

from zalo_ai.models.message import Message
from zalo_ai.models.message_batch import MessageBatch
from zalo_ai.summarizer.summarization_service import SummarizationService


def create_batch() -> MessageBatch:
    message = Message(
        message_id="msg_001",
        target_id="group_001",
        sender="Alice",
        content="The meeting is at 9 AM tomorrow.",
        timestamp=datetime(2026, 10, 11, 8, 0),
    )
    return MessageBatch(
        target_id="group_001",
        messages=[message],
    )


def test_summarize_returns_provider_result():
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Cuộc họp diễn ra lúc 9 giờ sáng mai."

    service = SummarizationService(provider=mock_provider)

    result = service.summarize(create_batch())

    
    assert result == "Cuộc họp diễn ra lúc 9 giờ sáng mai."
    mock_provider.generate.assert_called_once()


def test_summarize_sends_built_prompt_to_provider():
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Tóm tắt cuộc trò chuyện."

    service = SummarizationService(provider=mock_provider)
    batch = create_batch()

    response = service.summarize(batch)

    print(response)
     
    prompt = mock_provider.generate.call_args.args[0]
    assert "Summarize the following conversation in Vietnamese." in prompt
    assert "Alice: The meeting is at 9 AM tomorrow." in prompt
    assert "group_001" in prompt


def test_summarize_rejects_empty_batch():
    mock_provider = MagicMock()
    service = SummarizationService(provider=mock_provider)
    batch = MessageBatch(target_id="group_001", messages=[])

    with pytest.raises(ValueError, match="empty message batch"):
        service.summarize(batch)

    mock_provider.generate.assert_not_called()




from datetime import datetime

from zalo_ai.models.message import Message


def test_summarize_propagates_provider_error():
    mock_provider = MagicMock()
    mock_provider.generate.side_effect = RuntimeError(
        "Provider unavailable"
    )

    service = SummarizationService(provider=mock_provider)

    message = Message(
        message_id="msg_001",
        target_id="group_001",
        sender="Alice",
        content="Meeting at 9 AM.",
        timestamp=datetime(2026, 10, 12, 8, 0),
    )
    batch = MessageBatch(
        target_id="group_001",
        messages=[message],
    )

    with pytest.raises(RuntimeError, match="Provider unavailable"):
        service.summarize(batch)