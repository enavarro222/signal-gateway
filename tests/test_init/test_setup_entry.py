"""Tests for async_setup_entry function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.const import CONF_NAME

from custom_components.signal_gateway import async_setup_entry
from custom_components.signal_gateway.const import (
    CONF_PHONE_NUMBER,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
    EVENT_SIGNAL_RECEIVED,
)


@pytest.mark.asyncio
async def test_setup_entry_basic_without_websocket(mock_hass, mock_entry):
    """Test basic setup without websocket."""
    mock_entry.data[CONF_WEBSOCKET_ENABLED] = False

    with patch(
        "custom_components.signal_gateway.async_get_clientsession"
    ) as mock_session, patch(
        "custom_components.signal_gateway.SignalClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True
        assert "test_entry_id" in mock_hass.data[DOMAIN]
        assert mock_hass.data[DOMAIN]["test_entry_id"]["client"] == mock_client
        assert mock_hass.data[DOMAIN]["test_entry_id"]["service_name"] == "test_signal"
        assert mock_hass.data[DOMAIN]["test_entry_id"]["default_recipients"] == [
            "+9876543210",
            "+5551234567",
        ]
        mock_hass.config_entries.async_forward_entry_setups.assert_called_once()
        mock_entry.add_update_listener.assert_called_once()


@pytest.mark.asyncio
async def test_setup_entry_with_websocket(mock_hass, mock_entry):
    """Test setup with websocket enabled."""
    with patch(
        "custom_components.signal_gateway.async_get_clientsession"
    ) as mock_session, patch(
        "custom_components.signal_gateway.SignalClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.set_message_handler = MagicMock()
        mock_client.start_listening = AsyncMock()
        mock_client_class.return_value = mock_client

        result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True
        mock_client.set_message_handler.assert_called_once()
        mock_client.start_listening.assert_called_once()


@pytest.mark.asyncio
async def test_setup_entry_without_name_uses_domain(mock_hass, mock_entry):
    """Test that missing name defaults to domain."""
    mock_entry.data = {
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
        CONF_WEBSOCKET_ENABLED: False,
    }

    with patch("custom_components.signal_gateway.async_get_clientsession"), patch(
        "custom_components.signal_gateway.SignalClient"
    ):
        result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True
        assert (
            mock_hass.data[DOMAIN]["test_entry_id"]["service_name"] == "signal_gateway"
        )


@pytest.mark.asyncio
async def test_setup_entry_without_recipients(mock_hass, mock_entry):
    """Test setup without default recipients."""
    mock_entry.data = {
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
        CONF_NAME: "Test Signal",
        CONF_WEBSOCKET_ENABLED: False,
    }

    with patch("custom_components.signal_gateway.async_get_clientsession"), patch(
        "custom_components.signal_gateway.SignalClient"
    ):
        result = await async_setup_entry(mock_hass, mock_entry)

        assert result is True
        assert mock_hass.data[DOMAIN]["test_entry_id"]["default_recipients"] == []


@pytest.mark.asyncio
async def test_setup_entry_duplicate_service_name(mock_hass, mock_entry):
    """Test that duplicate service names are rejected."""
    # Add an existing entry with the same service name
    mock_hass.data[DOMAIN]["existing_entry_id"] = {
        "service_name": "test_signal",
    }

    with patch("custom_components.signal_gateway.async_get_clientsession"), patch(
        "custom_components.signal_gateway.SignalClient"
    ):
        result = await async_setup_entry(mock_hass, mock_entry)

        assert result is False
        assert "test_entry_id" not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_setup_entry_websocket_message_handler(mock_hass, mock_entry):
    """Test that websocket message handler fires events."""
    with patch("custom_components.signal_gateway.async_get_clientsession"), patch(
        "custom_components.signal_gateway.SignalClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.set_message_handler = MagicMock()
        mock_client.start_listening = AsyncMock()
        mock_client_class.return_value = mock_client

        await async_setup_entry(mock_hass, mock_entry)

        # Get the message handler that was registered
        handler = mock_client.set_message_handler.call_args[0][0]

        # Call the handler with test data
        test_data = {"sender": "+1234567890", "message": "Test message"}
        await handler(test_data)

        # Verify event was fired
        mock_hass.bus.async_fire.assert_called_once_with(
            EVENT_SIGNAL_RECEIVED, test_data
        )


@pytest.mark.asyncio
async def test_setup_entry_websocket_message_handler_error(mock_hass, mock_entry):
    """Test that websocket message handler handles errors gracefully."""
    with patch("custom_components.signal_gateway.async_get_clientsession"), patch(
        "custom_components.signal_gateway.SignalClient"
    ) as mock_client_class:
        mock_client = MagicMock()
        mock_client.set_message_handler = MagicMock()
        mock_client.start_listening = AsyncMock()
        mock_client_class.return_value = mock_client

        await async_setup_entry(mock_hass, mock_entry)

        # Get the message handler that was registered
        handler = mock_client.set_message_handler.call_args[0][0]

        # Make async_fire raise an exception
        mock_hass.bus.async_fire.side_effect = Exception("Test error")

        # Handler should not raise exception
        await handler({"test": "data"})
