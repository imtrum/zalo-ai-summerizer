
from zalo_ai.ai.providers.gemini_provider import GeminiProvider
from zalo_ai.ai.providers.mock_provider import MockProvider
from zalo_ai.config import settings


def create_provider():
    """Create the AI provider selected in configuration."""
    provider_name = settings.AI_PROVIDER.strip().lower()

    if provider_name == "gemini":
        return GeminiProvider()

    if provider_name == "mock":
        return MockProvider()

    raise ValueError(
        f"Unsupported AI provider: '{provider_name}'. "
        "Supported providers: 'gemini', 'mock'."
    )