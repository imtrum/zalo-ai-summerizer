
from zalo_ai.models.message import Message


def filter_messages_by_target_ids(
    messages: list[Message],
    target_ids: set[str],
) -> list[Message]:
    """Keep only messages belonging to the specified targets."""
    return [
        message
        for message in messages
        if message.target_id in target_ids
    ]