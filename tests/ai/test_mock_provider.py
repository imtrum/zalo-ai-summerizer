
import pytest

from zalo_ai.ai.providers.mock_provider import MockProvider


def test_generate_returns_mock_summary():
    provider = MockProvider()

    result = provider.generate("Summarize these messages.")

    assert result == "[MOCK SUMMARY] This is a test summary."


def test_generate_rejects_empty_prompt():
    provider = MockProvider()

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        provider.generate("   ")