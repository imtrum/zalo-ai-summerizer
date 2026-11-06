
from unittest.mock import patch

import pytest

from zalo_ai.ai.providers.mock_provider import MockProvider
from zalo_ai.ai.providers.provider_factory import create_provider


def test_create_provider_returns_mock_provider():
    with patch("zalo_ai.ai.providers.provider_factory.settings.AI_PROVIDER", "mock"):
        provider = create_provider()

    assert isinstance(provider, MockProvider)


def test_create_provider_rejects_unsupported_provider():
    with patch("zalo_ai.ai.providers.provider_factory.settings.AI_PROVIDER", "unknown"):
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            create_provider()