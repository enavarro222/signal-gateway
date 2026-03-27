import pytest
from unittest.mock import AsyncMock
from custom_components.signal_gateway.signal.client import SignalClient


def test_signal_client_initialization():
    """Test that SignalClient properly initializes with HTTP and WebSocket capabilities."""
    session = AsyncMock()
    client = SignalClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )
    # Verify HTTP client attributes (inherited from SignalHTTPClient)
    assert client.api_url == "http://localhost:8080"
    assert client.phone_number == "+33612345678"
    assert client.session == session
    # Verify WebSocket listener is created
    assert client._ws_listener is not None
    assert client._ws_listener.api_url == "http://localhost:8080"
    assert client._ws_listener.phone_number == "+33612345678"



def test_signal_client_set_message_handler():
    """Test that message handler is properly set on WebSocket listener."""
    session = AsyncMock()
    client = SignalClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )
    handler = lambda msg: None
    client.set_message_handler(handler)
    assert client._ws_listener._message_handler == handler


@pytest.mark.asyncio
async def test_signal_client_start_listening():
    """Test that start_listening delegates to WebSocket listener."""
    session = AsyncMock()
    client = SignalClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )
    client._ws_listener.connect = AsyncMock()
    await client.start_listening()
    client._ws_listener.connect.assert_called_once()


@pytest.mark.asyncio
async def test_signal_client_stop_listening():
    """Test that stop_listening delegates to WebSocket listener."""
    session = AsyncMock()
    client = SignalClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )
    client._ws_listener.disconnect = AsyncMock()
    await client.stop_listening()
    client._ws_listener.disconnect.assert_called_once()
