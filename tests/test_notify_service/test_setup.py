"""Tests for notify service setup and integration with Home Assistant."""

import pytest
from unittest.mock import MagicMock

from custom_components.signal_gateway.notify import async_setup_entry


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
