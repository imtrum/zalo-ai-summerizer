from zalo_ai.ai.providers.gemini_provider import GeminiProvider
from zalo_ai.models.message_batch import MessageBatch
from zalo_ai.summarizer.prompt_builder import build_summarization_prompt

class SummarizationService:
    """Coordinate prompt creation and AI-powered summarization."""


    def __init__(self, provider: GeminiProvider | None = None) -> None:
        self.provider = provider or GeminiProvider()

    def summarize(self, batch: MessageBatch) -> str:
        """Summarize a batch of messages using the configured AI provider."""
        if not batch.messages:
            raise ValueError("Cannot summarize an empty message batch.")

        prompt = build_summarization_prompt(batch)
        return self.provider.generate(prompt)

