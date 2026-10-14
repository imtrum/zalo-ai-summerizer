from unittest.mock import MagicMock, patch

import pytest

from zalo_ai.ai.providers.gemini_provider import GeminiProvider
from zalo_ai.config import settings


def test_generate_returns_gemini_response():
    mock_response = MagicMock()
    mock_response.text = " Đây là bản tóm tắt. "

    with patch(
        "zalo_ai.ai.providers.gemini_provider.genai.Client"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(settings, "GEMINI_API_KEY", "test-api-key"), \
            patch.object(settings, "AI_MODEL", "gemini-2.5-flash"):
            provider = GeminiProvider()
            result = provider.generate("Summarize these messages")

    assert result == "Đây là bản tóm tắt."
    mock_client.models.generate_content.assert_called_once()


def test_generate_rejects_empty_prompt():
    with patch.object(settings, "GEMINI_API_KEY", "test-api-key"):
        provider = GeminiProvider()

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        provider.generate("   ")


def test_init_rejects_missing_api_key():
    with patch.object(settings, "GEMINI_API_KEY", ""):
        with pytest.raises(ValueError, match="GEMINI_API_KEY is missing"):
            GeminiProvider()


def test_generate_rejects_empty_response():
    mock_response = MagicMock()
    mock_response.text = None

    with patch(
        "zalo_ai.ai.providers.gemini_provider.genai.Client"
    ) as mock_client_class:
        mock_client = mock_client_class.return_value
        mock_client.models.generate_content.return_value = mock_response

        with patch.object(settings, "GEMINI_API_KEY", "test-api-key"), \
             patch.object(settings, "AI_MODEL", "gemini-2.5-flash"):
            provider = GeminiProvider()

    with pytest.raises(RuntimeError, match="Gemini returned no text"):
        provider.generate("Summarize these messages")


def test_init_rejects_missing_model():
    with patch.object(settings, "GEMINI_API_KEY", "test-api-key"), \
         patch.object(settings, "AI_MODEL", ""):
            with pytest.raises(ValueError, match="AI_MODEL is missing"):
                GeminiProvider()
