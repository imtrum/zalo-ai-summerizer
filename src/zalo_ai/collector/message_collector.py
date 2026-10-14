import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from zalo_ai.models.message import Message


class MessageCollector(ABC):
    """Interface for collecting messages from a message source."""

    @abstractmethod
    def collect_messages(self) -> list[Message]:
        """Collect messages and return them as Message objects."""
        raise NotImplementedError



class JsonMessageCollector(MessageCollector):
    """Load messages from a local JSON file."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    def collect_messages(self) -> list[Message]:
        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Message file not found: {self.file_path}"
            )

        with self.file_path.open("r", encoding="utf-8") as file:
            records = json.load(file)

        if not isinstance(records, list):
            raise ValueError(
                "The JSON file must contain a list of messages."
            )

        messages: list[Message] = []

        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise ValueError(
                    f"Message at index {index} must be a JSON object."
                )

            try:
                message_data = record.copy()
                message_data["timestamp"] = datetime.fromisoformat(
                    message_data["timestamp"]
                )
                message = Message(**message_data)
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid message at index {index}: {exc}"
                ) from exc

            messages.append(message)

        return messages