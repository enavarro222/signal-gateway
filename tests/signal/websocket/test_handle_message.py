import pytest
import json
from unittest.mock import AsyncMock
from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)


@pytest.mark.asyncio
async def test_handle_message_valid(monkeypatch, mock_session):
    """
    Test that _handle_message correctly parses valid JSON and calls the handler.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080",
        phone_number="+33612345678",
        session=mock_session,
    )
    handler = AsyncMock()
    listener.set_message_handler(handler)
    valid_msg = {
        "envelope": {
            "dataMessage": {"message": "Hello, World!", "timestamp": 1234567890},
            "source": "+1234567890",
            "sourceDevice": 1,
        }
    }
    msg = json.dumps(valid_msg)
    await listener._handle_message(msg)
    handler.assert_awaited_once_with(valid_msg)


@pytest.mark.asyncio
async def test_handle_message_invalid_json(monkeypatch, caplog, mock_session):
    """
    Test that _handle_message logs an error if the message is not valid JSON.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080",
        phone_number="+33612345678",
        session=mock_session,
    )
    caplog.set_level("ERROR")
    await listener._handle_message("not a json")
    assert "Failed to parse WebSocket message" in caplog.text


@pytest.mark.asyncio
async def test_handle_message_handler_exception(monkeypatch, caplog, mock_session):
    """
    Test that _handle_message logs an error if the handler raises an exception.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080",
        phone_number="+33612345678",
        session=mock_session,
    )

    async def bad_handler(msg):
        raise Exception("fail")

    listener.set_message_handler(bad_handler)
    caplog.set_level("ERROR")
    valid_msg = {
        "envelope": {
            "dataMessage": {"message": "Test message", "timestamp": 1234567890},
            "source": "+1234567890",
        }
    }
    await listener._handle_message(json.dumps(valid_msg))
    assert "Error handling WebSocket message" in caplog.text
