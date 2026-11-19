from zalo_ai.models.message_batch import MessageBatch
from zalo_ai.summarizer.prompt_store import load_prompt


def build_summarization_prompt(
    batch: MessageBatch,
    instructions: str | None = None,
) -> str:
    """Build a prompt from saved instructions and one message batch."""
    formatted_messages = []

    for message in batch.get_messages():
        formatted_messages.append(
            f"[{message.timestamp.isoformat()}] "
            f"{message.sender}: {message.content}"
        )

    messages_text = "\n".join(formatted_messages)
    instructions = instructions or load_prompt()

    return (
        f"{instructions}\n\n"
        f"Target ID: {batch.target_id}\n\n"
        f"Messages:\n{messages_text}"
    )
