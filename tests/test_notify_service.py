"""Tests for Signal Gateway notify service."""

import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from custom_components.signal_gateway.notify import (
    SignalGatewayNotificationService,
    async_setup_entry,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


@pytest.fixture
def mock_signal_client():
    """Create a mock Signal client."""
    client = AsyncMock()
    client.send_message = AsyncMock(return_value={"success": True})
    return client


@pytest.fixture
def notification_service(mock_hass, mock_signal_client):
    """Create a notification service instance."""
    return SignalGatewayNotificationService(
        hass=mock_hass,
        client=mock_signal_client,
        default_recipients=["+1234567890"],
    )


# Test async_setup_entry
@pytest.mark.asyncio
async def test_async_setup_entry_no_client_data(mock_hass):
    """Test setup when client data is missing."""
    mock_entry = MagicMock()
    mock_entry.entry_id = "test_id"

    result = await async_setup_entry(mock_hass, mock_entry, None)
    assert result is False


@pytest.mark.asyncio
async def test_async_setup_entry_no_client(mock_hass):
    """Test setup when client is not initialized."""
    from custom_components.signal_gateway.const import DOMAIN

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_id"
    mock_hass.data[DOMAIN] = {"test_id": {}}  # No client key

    result = await async_setup_entry(mock_hass, mock_entry, None)
    assert result is False


@pytest.mark.asyncio
async def test_async_setup_entry_success(mock_hass, mock_signal_client):
    """Test successful setup."""
    from custom_components.signal_gateway.const import DOMAIN

    mock_entry = MagicMock()
    mock_entry.entry_id = "test_id"
    mock_hass.data[DOMAIN] = {
        "test_id": {
            "client": mock_signal_client,
            "default_recipients": ["+1234567890"],
            "service_name": "test_signal",
        }
    }

    result = await async_setup_entry(mock_hass, mock_entry, None)
    assert result is True
    mock_hass.services.async_register.assert_called_once()


# Test _fix_phone_number
def test_fix_phone_number_with_plus():
    """Test phone number that already has +."""
    result = SignalGatewayNotificationService._fix_phone_number("+1234567890")
    assert result == "+1234567890"


def test_fix_phone_number_without_plus():
    """Test phone number missing +."""
    result = SignalGatewayNotificationService._fix_phone_number("1234567890")
    assert result == "+1234567890"


def test_fix_phone_number_group_id():
    """Test that group IDs are not modified."""
    result = SignalGatewayNotificationService._fix_phone_number("group.abc123")
    assert result == "group.abc123"


def test_fix_phone_number_non_numeric():
    """Test that non-numeric strings are not modified."""
    result = SignalGatewayNotificationService._fix_phone_number("notanumber")
    assert result == "notanumber"


# Test _normalize_file_path
def test_normalize_file_path_success(notification_service):
    """Test normalizing valid file path."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test")
        tmp.flush()
        tmp_path = tmp.name

    try:
        result = notification_service._normalize_file_path(tmp_path)
        assert result == Path(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_normalize_file_path_with_file_scheme(notification_service):
    """Test normalizing file:// URL."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test")
        tmp.flush()
        tmp_path = tmp.name

    try:
        result = notification_service._normalize_file_path(f"file://{tmp_path}")
        assert result == Path(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_normalize_file_path_not_exists(notification_service):
    """Test normalizing non-existent file."""
    with pytest.raises(ValueError, match="not found"):
        notification_service._normalize_file_path("/nonexistent/file.txt")


def test_normalize_file_path_is_directory(notification_service):
    """Test normalizing directory path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="not a file"):
            notification_service._normalize_file_path(tmpdir)


# Test _normalize_targets
def test_normalize_targets_string(notification_service):
    """Test normalizing single string target."""
    result = notification_service._normalize_targets("+9876543210")
    assert result == ["+9876543210"]


def test_normalize_targets_list(notification_service):
    """Test normalizing list of targets."""
    result = notification_service._normalize_targets(["+111", "+222"])
    assert result == ["+111", "+222"]


def test_normalize_targets_none_with_defaults(notification_service):
    """Test normalizing None target with default recipients."""
    result = notification_service._normalize_targets(None)
    assert result == ["+1234567890"]


def test_normalize_targets_none_without_defaults(mock_hass, mock_signal_client):
    """Test normalizing None target without default recipients."""
    service = SignalGatewayNotificationService(
        hass=mock_hass,
        client=mock_signal_client,
        default_recipients=None,
    )
    result = service._normalize_targets(None)
    assert result is None


# Test _prepare_message
def test_prepare_message_without_title(notification_service):
    """Test preparing message without title."""
    result = notification_service._prepare_message("Hello", None)
    assert result == "Hello"


def test_prepare_message_with_title(notification_service):
    """Test preparing message with title."""
    result = notification_service._prepare_message("Body", "Title")
    assert result == "Title\nBody"


# Test _encode_attachments_from_paths
def test_encode_attachments_success(notification_service):
    """Test encoding attachments from paths."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"test content")
        tmp.flush()
        tmp_path = tmp.name

    try:
        result = notification_service._encode_attachments_from_paths([tmp_path])
        assert len(result) == 1
        # Verify it's base64 encoded
        import base64

        decoded = base64.b64decode(result[0])
        assert decoded == b"test content"
    finally:
        os.unlink(tmp_path)


def test_encode_attachments_file_not_found(notification_service):
    """Test encoding non-existent file."""
    with pytest.raises(ValueError, match="not found"):
        notification_service._encode_attachments_from_paths(["/nonexistent.txt"])


def test_encode_attachments_too_large(notification_service):
    """Test encoding file exceeding size limit."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        # Write 51 MB
        tmp.write(b"x" * (51 * 1024 * 1024))
        tmp.flush()
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="exceeds maximum"):
            notification_service._encode_attachments_from_paths([tmp_path])
    finally:
        os.unlink(tmp_path)


def test_encode_attachments_multiple_files(notification_service):
    """Test encoding multiple attachments."""
    files = []
    try:
        for i in range(2):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            tmp.write(f"content{i}".encode())
            tmp.flush()
            files.append(tmp.name)
            tmp.close()

        result = notification_service._encode_attachments_from_paths(files)
        assert len(result) == 2
    finally:
        for f in files:
            os.unlink(f)


# Test _validate_content_length
def test_validate_content_length_ok(notification_service):
    """Test content length validation with acceptable size."""
    # Should not raise
    notification_service._validate_content_length("1000", 2000)


def test_validate_content_length_too_large(notification_service):
    """Test content length validation with size exceeding limit."""
    # Should raise when Content-Length exceeds max_size
    with pytest.raises(ValueError):
        notification_service._validate_content_length("2000", 1000)


def test_validate_content_length_none(notification_service):
    """Test content length validation with no header."""
    # Should not raise
    notification_service._validate_content_length(None, 1000)


# Test _download_in_chunks
@pytest.mark.asyncio
async def test_download_in_chunks_success(notification_service):
    """Test successful chunk download."""
    mock_response = MagicMock()

    chunks_data = [b"chunk1", b"chunk2"]

    async def mock_iter_chunked(size):
        for chunk in chunks_data:
            yield chunk

    mock_response.content.iter_chunked = mock_iter_chunked

    result = await notification_service._download_in_chunks(mock_response, 10000)
    assert result == b"chunk1chunk2"


@pytest.mark.asyncio
async def test_download_in_chunks_exceeds_limit(notification_service):
    """Test download exceeding size limit."""
    mock_response = MagicMock()

    async def mock_iter_chunked(size):
        # Yield chunks that exceed the limit
        for _ in range(10):
            yield b"x" * 1000

    mock_response.content.iter_chunked = mock_iter_chunked

    with pytest.raises(ValueError):
        await notification_service._download_in_chunks(mock_response, 100)


# Test _send_to_recipient
@pytest.mark.asyncio
async def test_send_to_recipient_success(notification_service, mock_signal_client):
    """Test successful send to recipient."""
    await notification_service._send_to_recipient("+1234567890", "Hello", None)

    # Check the call was made with correct parameters
    mock_signal_client.send_message.assert_called_once()
    call_kwargs = mock_signal_client.send_message.call_args[1]
    assert call_kwargs["target"] == "+1234567890"
    assert call_kwargs["message"] == "Hello"
    assert call_kwargs["base64_attachments"] is None


@pytest.mark.asyncio
async def test_send_to_recipient_with_attachments(
    notification_service, mock_signal_client
):
    """Test send with attachments."""
    attachments = ["base64data"]
    await notification_service._send_to_recipient("+1234567890", "Hello", attachments)

    mock_signal_client.send_message.assert_called_once()
    call_kwargs = mock_signal_client.send_message.call_args[1]
    assert call_kwargs["base64_attachments"] == attachments


@pytest.mark.asyncio
async def test_send_to_recipient_error(notification_service, mock_signal_client):
    """Test send with client error."""
    mock_signal_client.send_message.side_effect = Exception("Send failed")

    # Should not raise, just log
    await notification_service._send_to_recipient("+1234567890", "Hello", None)


# Test async_send_message
@pytest.mark.asyncio
async def test_async_send_message_no_target_no_default(mock_hass, mock_signal_client):
    """Test send without target and without defaults."""
    service = SignalGatewayNotificationService(
        hass=mock_hass,
        client=mock_signal_client,
        default_recipients=None,
    )

    await service.async_send_message(message="Test")

    # Should not send
    mock_signal_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_async_send_message_with_title(notification_service, mock_signal_client):
    """Test send with title."""
    await notification_service.async_send_message(
        message="Body", title="Title", target="+1111111111"
    )

    mock_signal_client.send_message.assert_called_once()
    call_kwargs = mock_signal_client.send_message.call_args[1]
    message_sent = call_kwargs["message"]
    assert "Title" in message_sent
    assert "Body" in message_sent


@pytest.mark.asyncio
async def test_async_send_message_multiple_targets(
    notification_service, mock_signal_client
):
    """Test send to multiple targets."""
    await notification_service.async_send_message(
        message="Hello", target=["+1111111111", "+2222222222"]
    )

    # Should be called twice
    assert mock_signal_client.send_message.call_count == 2


@pytest.mark.asyncio
async def test_async_send_message_with_local_attachments(
    notification_service, mock_signal_client
):
    """Test send with local file attachments."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"test")
        tmp.flush()
        tmp_path = tmp.name

    try:
        await notification_service.async_send_message(
            message="Hello", target="+1111111111", attachments=[tmp_path]
        )

        # Should be called with base64 attachments
        mock_signal_client.send_message.assert_called_once()
        call_kwargs = mock_signal_client.send_message.call_args[1]
        assert call_kwargs["base64_attachments"] is not None
        assert len(call_kwargs["base64_attachments"]) == 1
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_async_send_message_attachment_processing_fails(
    notification_service, mock_signal_client
):
    """Test send when attachment processing fails - should raise exception to notify user."""
    with pytest.raises(ValueError, match="not found"):
        await notification_service.async_send_message(
            message="Hello",
            target="+1111111111",
            attachments=["/nonexistent.txt"],  # Will raise ValueError
        )

    # Message should not be sent when attachments fail
    mock_signal_client.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_process_attachments_both_local_and_urls(notification_service):
    """Test processing both local files and URLs."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"local")
        tmp.flush()
        tmp_path = tmp.name

    try:
        # Mock URL download
        with patch.object(
            notification_service,
            "_download_attachments_from_urls",
            return_value=["url_base64"],
        ):
            result = await notification_service._process_attachments(
                attachments=[tmp_path],
                urls=["https://example.com/file.jpg"],
                verify_ssl=True,
            )

            assert result is not None
            assert len(result) == 2  # 1 local + 1 url
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_process_attachments_exception_propagates(notification_service):
    """Test that exceptions in attachment processing propagate to the caller."""
    with pytest.raises(ValueError, match="Attachment file not found"):
        await notification_service._process_attachments(
            attachments=["/nonexistent.txt"], urls=None, verify_ssl=True
        )


# Test text_mode parameter
@pytest.mark.asyncio
async def test_send_message_with_styled_mode(notification_service, mock_signal_client):
    """Test sending message with styled text mode."""
    await notification_service.async_send_message(
        message="**Bold** text",
        target="+1234567890",
        text_mode="styled",
    )

    mock_signal_client.send_message.assert_called_once()
    call_kwargs = mock_signal_client.send_message.call_args.kwargs
    assert call_kwargs["text_mode"] == "styled"
    assert call_kwargs["message"] == "**Bold** text"


@pytest.mark.asyncio
async def test_send_message_with_normal_mode(notification_service, mock_signal_client):
    """Test sending message with normal text mode."""
    await notification_service.async_send_message(
        message="Plain text",
        target="+1234567890",
        text_mode="normal",
    )

    mock_signal_client.send_message.assert_called_once()
    call_kwargs = mock_signal_client.send_message.call_args.kwargs
    assert call_kwargs["text_mode"] == "normal"


@pytest.mark.asyncio
async def test_send_message_default_normal(notification_service, mock_signal_client):
    """Test that text_mode defaults to 'normal'."""
    await notification_service.async_send_message(
        message="Test message",
        target="+1234567890",
    )

    mock_signal_client.send_message.assert_called_once()
    call_kwargs = mock_signal_client.send_message.call_args.kwargs
    assert call_kwargs["text_mode"] == "normal"


@pytest.mark.asyncio
async def test_send_message_with_formatted_content(
    notification_service, mock_signal_client
):
    """Test sending message with various markdown-like formatting."""
    formatted_message = "**Bold** *italic* ~strikethrough~ `monospace` ||spoiler||"

    await notification_service.async_send_message(
        message=formatted_message,
        target="+1234567890",
        text_mode="styled",
    )

    mock_signal_client.send_message.assert_called_once()
    call_kwargs = mock_signal_client.send_message.call_args.kwargs
    assert call_kwargs["message"] == formatted_message
    assert call_kwargs["text_mode"] == "styled"
