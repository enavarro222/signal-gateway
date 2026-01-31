"""Tests for async_unload_entry function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.signal_gateway import async_unload_entry
from custom_components.signal_gateway.const import DOMAIN


@pytest.mark.asyncio
async def test_unload_entry_success(mock_hass, mock_entry_minimal):
    """Test successful unload."""
    mock_client = MagicMock()
    mock_client.stop_listening = AsyncMock()

    mock_hass.data[DOMAIN]["test_entry_id"] = {
        "client": mock_client,
        "service_name": "test_signal",
    }

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
    mock_hass.data[DOMAIN]["test_entry_id"] = {
        "service_name": "test_signal",
    }

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
    """Test unload when platform unload fails."""
    mock_client = MagicMock()
    mock_client.stop_listening = AsyncMock()

    mock_hass.data[DOMAIN]["test_entry_id"] = {
        "client": mock_client,
        "service_name": "test_signal",
    }
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=False)

    with patch(
        "custom_components.signal_gateway.async_unload_notify_service"
    ) as mock_unload:
        mock_unload.return_value = AsyncMock()

        result = await async_unload_entry(mock_hass, mock_entry_minimal)

        assert result is False
        # Entry should not be removed if unload fails
        assert "test_entry_id" in mock_hass.data[DOMAIN]
        # WebSocket should NOT be stopped if unload failed
        mock_client.stop_listening.assert_not_called()
        # Notify service should NOT be unloaded if platform unload failed
        mock_unload.assert_not_called()
