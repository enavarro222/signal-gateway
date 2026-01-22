import pytest
from unittest.mock import AsyncMock
from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)


@pytest.mark.asyncio
async def test_websocket_listener_set_message_handler():
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="+33612345678"
    )
    handler = lambda msg: None
    listener.set_message_handler(handler)
    assert listener._message_handler == handler
