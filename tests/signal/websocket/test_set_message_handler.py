import pytest
from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)


def test_set_message_handler():
    """
    Test that set_message_handler correctly assigns the handler.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="+33612345678"
    )
    handler = lambda msg: None
    listener.set_message_handler(handler)
    assert listener._message_handler == handler
