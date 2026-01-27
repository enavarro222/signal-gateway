import pytest
import asyncio
import json
from unittest.mock import AsyncMock
from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)
from .conftest import MockWebSocketClient


@pytest.mark.asyncio
async def test_listen_stops_when_running_becomes_false(
    mock_websocket_connects, monkeypatch
):
    """
    Test that _listen exits cleanly when _running is set to False (e.g., by disconnect).
    """
    # Prepare a websocket mock that yields two messages
    messages = [
        json.dumps({"msg": 1}),
    ]

    async def websockets_clients_generator(*args, **kwargs):
        async def websocket_messages_generator():
            for msg in messages:
                yield msg

        yield MockWebSocketClient(websocket_messages_generator)

    mock_websocket_connects.set_clients_generator(websockets_clients_generator)

    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="123"
    )
    handler = AsyncMock()
    listener.set_message_handler(handler)
    listener._running = True

    # Patch _connect_and_listen to set _running to False after first call
    orig_connect_and_listen = listener._connect_and_listen

    async def connect_and_listen_once(ws_url):
        await orig_connect_and_listen(ws_url)
        listener._running = False
        raise ValueError("Stop listening after one connection")

    monkeypatch.setattr(listener, "_connect_and_listen", connect_and_listen_once)

    await listener._listen()
    # Only one message should be handled
    handler.assert_awaited_once_with({"msg": 1})
