from datetime import datetime

from zalo_ai.models.message import Message
from zalo_ai.models.message_batch import MessageBatch
from zalo_ai.summarizer.summarization_service import SummarizationService


def main() -> None:
    messages = [
        Message(
            message_id="msg_001",
            target_id="group_001",
            sender="Alice",
            content="Cuộc họp dự án sẽ diễn ra lúc 9 giờ sáng mai.",
            timestamp=datetime(2026, 10, 11, 8, 0),
        ),
        Message(
            message_id="msg_002",
            target_id="group_001",
            sender="Bob",
            content="Tôi sẽ chuẩn bị báo cáo trước cuộc họp.",
            timestamp=datetime(2026, 10, 11, 8, 5),
        ),
    ]

    batch = MessageBatch(
        target_id="group_001",
        messages=messages,
    )

    service = SummarizationService()
    summary = service.summarize(batch)

    print("\n=== Gemini Summary ===")
    print(summary)


if __name__ == "__main__":
    main()