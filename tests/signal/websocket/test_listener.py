import asyncio
import json
from unittest.mock import AsyncMock
import pytest

from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)

from .conftest import MockWebSocketClient


@pytest.mark.asyncio
async def test__listen_receives_message(mock_websocket_connects, mock_session):
    """
    Test that _listen receives a message and calls the handler.
    """

    # configure the websocket mock
    async def websockets_clients_generator(*args, **kwargs):
        async def websocket_messages_generator():
            yield json.dumps({"data": "test"})

        yield MockWebSocketClient(websocket_messages_generator)

    mock_websocket_connects.set_clients_generator(websockets_clients_generator)

    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="123", session=mock_session
    )
    handler = AsyncMock()
    listener.set_message_handler(handler)
    listener._running = True

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(listener._listen(), timeout=2)
    handler.assert_awaited_once_with({"data": "test"})


@pytest.mark.asyncio
async def test__listen_connection_error(mock_websocket_connects, mock_session):
    """
    Test that _listen stops running after repeated connection errors.
    """

    async def websockets_clients_generator(*args, **kwargs):
        print("Raising connection error")
        raise Exception("connection failed")

    mock_websocket_connects.set_clients_generator(websockets_clients_generator)

    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="123", session=mock_session
    )
    listener.max_retries = 3
    listener.retry_delay = 0.1
    listener._running = True
    # Limit retries so the test does not loop too long
    await asyncio.wait_for(listener._listen(), timeout=20)
    assert not listener._running
