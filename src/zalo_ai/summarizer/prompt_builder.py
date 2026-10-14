
from zalo_ai.models.message_batch import MessageBatch


def build_summarization_prompt(batch: MessageBatch) -> str:
    """Build a prompt containing the messages to summarize."""
    formatted_messages = []

    for message in batch.get_messages():
        formatted_messages.append(
            f"[{message.timestamp.isoformat()}] "
            f"{message.sender}: {message.content}"
        )

    messages_text = "\n".join(formatted_messages)

    return (
        "Summarize the following conversation in Vietnamese.\n"
        "Preserve important information, decisions, tasks, and deadlines.\n"
        "Do not invent information that is not present in the messages.\n\n"
        f"Target ID: {batch.target_id}\n\n"
        f"Messages:\n{messages_text}"
    )