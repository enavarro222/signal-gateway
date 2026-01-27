from unittest.mock import Mock, AsyncMock
import pytest
import aiohttp


class MockWSMessage:
    """Mock aiohttp WebSocket message."""

    def __init__(self, data=None, msg_type=None):
        self.data = data
        self.type = msg_type if msg_type is not None else aiohttp.WSMsgType.TEXT


class MockWebSocketClient:
    def __init__(self, message_generator_func):
        self.generator = message_generator_func()
        self.closed = False
        self._exception = None

    def set_message_generator(self, message_generator_func):
        self.generator = message_generator_func()

    def exception(self):
        return self._exception

    async def close(self):
        self.closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            msg_data = await anext(self.generator)
            # If it's already a MockWSMessage, return it
            if isinstance(msg_data, MockWSMessage):
                return msg_data
            # Otherwise wrap string in TEXT message
            return MockWSMessage(msg_data, aiohttp.WSMsgType.TEXT)
        except StopAsyncIteration:
            return MockWSMessage(None, aiohttp.WSMsgType.CLOSED)


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


class MockSession:
    """Mock aiohttp ClientSession."""

    def __init__(self, ws_connect_mock):
        self.ws_connect = ws_connect_mock
        self.closed = False

    async def close(self):
        self.closed = True


# Fixture for a mocked websocket connection supporting async context manager
@pytest.fixture
def mock_websocket_connects(monkeypatch):
    websocket_connects = MockWebSocketConnection()
    yield websocket_connects


@pytest.fixture
def mock_session(mock_websocket_connects):
    """Mock aiohttp session with ws_connect."""
    return MockSession(mock_websocket_connects)
