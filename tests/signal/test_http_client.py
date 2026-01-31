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
    result = await client.send_message("+33698765432", "Hello", base64_attachments=None)
    assert result == {"result": "ok"}


@pytest.mark.asyncio
async def test_http_client_send_message_with_styled_mode():
    """Test sending a message with styled text mode."""
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
    result = await client.send_message(
        "+33698765432", "**Bold** and *italic*", text_mode="styled"
    )

    # Verify the payload includes text_mode
    call_args = session.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["text_mode"] == "styled"
    assert payload["message"] == "**Bold** and *italic*"
    assert result == {"result": "ok"}


@pytest.mark.asyncio
async def test_http_client_send_message_with_normal_mode():
    """Test sending a message with normal text mode."""
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
    result = await client.send_message("+33698765432", "Plain text", text_mode="normal")

    # Verify the payload includes text_mode
    call_args = session.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["text_mode"] == "normal"
    assert result == {"result": "ok"}


@pytest.mark.asyncio
async def test_http_client_send_message_default_normal():
    """Test that text_mode defaults to 'normal'."""
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
    # Call without specifying text_mode
    result = await client.send_message("+33698765432", "Test message")

    # Verify the default is "normal"
    call_args = session.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["text_mode"] == "normal"
    assert result == {"result": "ok"}
