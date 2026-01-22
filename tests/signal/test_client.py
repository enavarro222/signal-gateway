import pytest
from unittest.mock import AsyncMock
from custom_components.signal_gateway.signal.client import SignalClient


@pytest.mark.asyncio
async def test_signal_client_send_message():
    session = AsyncMock()
    client = SignalClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )
    # Patch the HTTP client's send_message method
    client._http_client.send_message = AsyncMock(return_value={"success": True})
    result = await client.send_message("+33698765432", "Hello", attachments=None)
    assert result == {"success": True}


def test_signal_client_set_message_handler():
    session = AsyncMock()
    client = SignalClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )
    handler = lambda msg: None
    client.set_message_handler(handler)
    assert client._ws_listener._message_handler == handler
