import pytest
from unittest.mock import Mock, AsyncMock
from custom_components.signal_gateway.signal.http_client import SignalHTTPClient


@pytest.mark.asyncio
async def test_http_client_send_message_success():
    # Préparer le mock de session.post pour qu'il soit une coroutine qui retourne un context manager async
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"result": "ok"})

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = response

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )
    result = await client.send_message("+33698765432", "Hello", attachments=None)
    assert result == {"result": "ok"}
