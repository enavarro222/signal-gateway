"""Tests for async_reload_entry function."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.signal_gateway import async_reload_entry


@pytest.mark.asyncio
async def test_reload_entry():
    """Test reload calls unload then setup."""
    mock_hass = MagicMock(spec=HomeAssistant)
    mock_entry = MagicMock(spec=ConfigEntry)

    with patch(
        "custom_components.signal_gateway.async_unload_entry"
    ) as mock_unload, patch(
        "custom_components.signal_gateway.async_setup_entry"
    ) as mock_setup:
        mock_unload.return_value = AsyncMock(return_value=True)
        mock_setup.return_value = AsyncMock(return_value=True)

        await async_reload_entry(mock_hass, mock_entry)

        mock_unload.assert_called_once_with(mock_hass, mock_entry)
        mock_setup.assert_called_once_with(mock_hass, mock_entry)
