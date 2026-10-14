import pytest

from zalo_ai.collector.message_collector import MessageCollector


def test_message_collector_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        MessageCollector()