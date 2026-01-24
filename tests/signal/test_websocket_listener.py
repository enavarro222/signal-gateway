import asyncio
import json
from unittest.mock import AsyncMock, Mock
import pytest

import websockets

from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)


class MockWebSocketClient:
    def __init__(self, message_generator_func):
        self.generator = message_generator_func()

    def set_message_generator(self, message_generator_func):
        self.generator = message_generator_func()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return await anext(self.generator)
        except StopAsyncIteration:
            raise websockets.exceptions.ConnectionClosed(Mock(), None)


class MockWebSocketConnection:
    def __init__(self, generator_func=None):
        if generator_func is None:

            async def default_generator():
                while True:
                    yield MockWebSocketClient(lambda: iter([]))

            generator_func = default_generator
        self.generator = generator_func()

    def set_clients_generator(self, generator_func):
        self.generator = generator_func()

    async def __aenter__(self):
        try:
            return await anext(self.generator)
        except StopAsyncIteration:
            raise Exception("No more websocket connections available")

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def __call__(self, *args, **kwds):
        return self


# Fixture for a mocked websocket connection supporting async context manager
@pytest.fixture
def mock_websocket_connects(monkeypatch):
    websocket_connects = MockWebSocketConnection()
    monkeypatch.setattr("websockets.connect", websocket_connects)
    yield websocket_connects


@pytest.mark.asyncio
async def test_websocket_listener_set_message_handler():
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="+33612345678"
    )
    handler = lambda msg: None
    listener.set_message_handler(handler)
    assert listener._message_handler == handler


@pytest.mark.asyncio
async def test__listen_receives_message(mock_websocket_connects):
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
        api_url="http://localhost:8080", phone_number="123"
    )
    handler = AsyncMock()
    listener.set_message_handler(handler)
    listener._running = True

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(listener._listen(), timeout=2)
    handler.assert_awaited_once_with({"data": "test"})


@pytest.mark.asyncio
async def test__listen_connection_error(mock_websocket_connects):
    """
    Test that _listen stops running after repeated connection errors.
    """

    async def websockets_clients_generator(*args, **kwargs):
        print("Raising connection error")
        raise Exception("connection failed")

    mock_websocket_connects.set_clients_generator(websockets_clients_generator)

    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="123"
    )
    listener.max_retries = 3
    listener.retry_delay = 0.1
    listener._running = True
    # Limit retries so the test does not loop too long
    await asyncio.wait_for(listener._listen(), timeout=20)
    assert not listener._running
