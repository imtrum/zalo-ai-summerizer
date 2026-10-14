
from collections import defaultdict

from zalo_ai.models.message import Message
from zalo_ai.models.message_batch import MessageBatch


def create_batches(messages: list[Message]) -> list[MessageBatch]:
    """Group messages into batches by target ID."""
    grouped: dict[str, list[Message]] = defaultdict(list)

    for message in messages:
        grouped[message.target_id].append(message)

    return [
        MessageBatch(target_id=target_id, messages=target_messages)
        for target_id, target_messages in grouped.items()
    ]