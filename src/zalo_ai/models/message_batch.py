
from dataclasses import dataclass

from zalo_ai.models.message import Message


@dataclass
class MessageBatch:
    target_id: str
    messages: list[Message]

    def __post_init__(self) -> None:
        if not self.target_id.strip():
            raise ValueError("target_id cannot be empty")

        for message in self.messages:
            if message.target_id != self.target_id:
                raise ValueError(
                    f"Message {message.message_id} belongs to "
                    f"target '{message.target_id}', not '{self.target_id}'"
                )

    def get_messages(self) -> list[Message]:
        return self.messages

    def get_message_count(self) -> int:
        return len(self.messages)