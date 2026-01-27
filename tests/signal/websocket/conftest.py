from unittest.mock import Mock
import pytest

import websockets


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
