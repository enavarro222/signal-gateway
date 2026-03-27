"""Tests for async_unload_entry function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.signal_gateway import async_unload_entry
from custom_components.signal_gateway.data import SignalGatewayEntryData
from custom_components.signal_gateway.const import DOMAIN


@pytest.mark.asyncio
async def test_unload_entry_success(mock_hass, mock_entry_minimal):
    """Test successful unload."""
    mock_client = MagicMock()
    mock_client.stop_listening = AsyncMock()

    mock_hass.data[DOMAIN]["test_entry_id"] = SignalGatewayEntryData(
        client=mock_client,
        service_name="test_signal",
        default_recipients=[],
    )

    with patch(
        "custom_components.signal_gateway.async_unload_notify_service"
    ) as mock_unload:
        mock_unload.return_value = AsyncMock()

        result = await async_unload_entry(mock_hass, mock_entry_minimal)

        assert result is True
        mock_client.stop_listening.assert_called_once()
        assert "test_entry_id" not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry_no_client(mock_hass, mock_entry_minimal):
    """Test unload when no client exists."""
    mock_hass.data[DOMAIN]["test_entry_id"] = SignalGatewayEntryData(
        client=None,
        service_name="test_signal",
        default_recipients=[],
    )

    with patch(
        "custom_components.signal_gateway.async_unload_notify_service"
    ) as mock_unload:
        mock_unload.return_value = AsyncMock()

        result = await async_unload_entry(mock_hass, mock_entry_minimal)

        assert result is True
        assert "test_entry_id" not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry_not_exists(mock_hass, mock_entry_minimal):
    """Test unload when entry doesn't exist in data."""
    with patch(
        "custom_components.signal_gateway.async_unload_notify_service"
    ) as mock_unload:
        mock_unload.return_value = AsyncMock()

        result = await async_unload_entry(mock_hass, mock_entry_minimal)

        # Should still succeed even if entry doesn't exist
        assert result is True
        # Verify it doesn't crash when popping non-existent entry
        assert "test_entry_id" not in mock_hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry_platform_fails(mock_hass, mock_entry_minimal):
    """Test unload when platform unload fails - continues cleanup anyway."""
    mock_client = MagicMock()
    mock_client.stop_listening = AsyncMock()

    mock_hass.data[DOMAIN]["test_entry_id"] = SignalGatewayEntryData(
        client=mock_client,
        service_name="test_signal",
        default_recipients=[],
    )
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    with patch(
        "custom_components.signal_gateway.async_unload_notify_service"
    ) as mock_unload:
        mock_unload.return_value = AsyncMock()

        result = await async_unload_entry(mock_hass, mock_entry_minimal)

        # Now returns True even if platform unload fails, to continue cleanup
        assert result is True
        # Entry should be removed even if unload fails partially
        assert "test_entry_id" not in mock_hass.data[DOMAIN]
        # WebSocket should be stopped to ensure cleanup
        mock_client.stop_listening.assert_called_once()
        # Notify service should be unloaded before platform unload
        mock_unload.assert_called_once()
