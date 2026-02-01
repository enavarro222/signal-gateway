"""Tests for notify service message sending operations."""

import os
import tempfile
import pytest


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
    from custom_components.signal_gateway.notify import SignalGatewayNotificationService

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
