"""Shared message collection interface."""

from abc import ABC, abstractmethod

from zalo_ai.models.message import Message


class MessageCollector(ABC):
    """Interface for collecting messages from a message source."""

    @abstractmethod
    def collect_messages(self) -> list[Message]:
        """Collect messages and return them as Message objects."""
        raise NotImplementedError
