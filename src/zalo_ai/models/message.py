
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    """Represent a single chat message."""

    message_id: str
    target_id: str
    sender: str
    content: str
    timestamp: datetime