import pytest
from unittest.mock import Mock
from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)


def test_set_message_handler(mock_session):
    """
    Test that set_message_handler correctly assigns the handler.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080",
        phone_number="+33612345678",
        session=mock_session,
    )
    handler = lambda msg: None
    listener.set_message_handler(handler)
    assert listener._message_handler == handler
