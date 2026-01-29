"""Tests for HTTP client error handling and edge cases."""

import pytest
from unittest.mock import Mock, AsyncMock
import aiohttp
import json as json_module
from custom_components.signal_gateway.signal.http_client import SignalHTTPClient


@pytest.mark.asyncio
async def test_send_message_api_error_status():
    """Test handling of non-200 status from API."""
    response = AsyncMock()
    response.status = 500
    response.text = AsyncMock(return_value="Internal Server Error")

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = response

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )

    with pytest.raises(RuntimeError, match="Signal API error: 500"):
        await client.send_message("+33698765432", "Hello")


@pytest.mark.asyncio
async def test_send_message_api_error_404():
    """Test handling of 404 status from API."""
    response = AsyncMock()
    response.status = 404
    response.text = AsyncMock(return_value="Not Found")

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = response

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )

    with pytest.raises(RuntimeError, match="Signal API error: 404"):
        await client.send_message("+33698765432", "Hello")


@pytest.mark.asyncio
async def test_send_message_json_parse_error():
    """Test handling of invalid JSON response."""
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="Invalid JSON response")
    response.json = AsyncMock(side_effect=json_module.JSONDecodeError("msg", "doc", 0))

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = response

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )

    result = await client.send_message("+33698765432", "Hello")

    # Should return success with text response
    assert result["success"] is True
    assert result["response"] == "Invalid JSON response"


@pytest.mark.asyncio
async def test_send_message_content_type_error():
    """Test handling of wrong content type."""
    response = AsyncMock()
    response.status = 200
    response.text = AsyncMock(return_value="Text response")
    response.json = AsyncMock(
        side_effect=aiohttp.ContentTypeError(request_info=Mock(), history=())
    )

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = response

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )

    result = await client.send_message("+33698765432", "Hello")

    assert result["success"] is True
    assert result["response"] == "Text response"


@pytest.mark.asyncio
async def test_send_message_network_error():
    """Test handling of network connection errors."""
    mock_cm = AsyncMock()
    mock_cm.__aenter__.side_effect = aiohttp.ClientError("Connection failed")

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await client.send_message("+33698765432", "Hello")


@pytest.mark.asyncio
async def test_send_message_with_attachments():
    """Test sending message with base64 attachments."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"success": True})

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = response

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )

    base64_data = ["iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"]
    result = await client.send_message("+33698765432", "Hello", base64_data)

    assert result == {"success": True}

    # Verify attachments were included in the request
    call_args = session.post.call_args
    assert call_args is not None
    json_data = call_args[1]["json"]
    assert "base64_attachments" in json_data
    assert json_data["base64_attachments"] == base64_data


@pytest.mark.asyncio
async def test_send_message_to_group():
    """Test sending message to a group ID."""
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={"success": True})

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = response

    session = AsyncMock()
    session.post = Mock(return_value=mock_cm)

    client = SignalHTTPClient(
        api_url="http://localhost:8080", phone_number="+33612345678", session=session
    )

    group_id = "group.abc123"
    result = await client.send_message(group_id, "Hello group")

    assert result == {"success": True}

    # Verify group ID was used as recipient
    call_args = session.post.call_args
    json_data = call_args[1]["json"]
    assert json_data["recipients"] == [group_id]
