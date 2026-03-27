"""Tests for fetch_available_devices helper function."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.signal_gateway.config_flow.discovery import (
    fetch_available_devices,
)


@pytest.mark.asyncio
async def test_fetch_available_devices_success(mock_hass, mock_contacts, mock_groups):
    """Test fetch_available_devices returns devices successfully."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.discover_devices",
        new_callable=AsyncMock,
    ) as mock_discover:
        mock_discover.return_value = {
            "contact_+33612345678": "John Doe",
            "group_abc123": "Test Group",
        }

        devices, error = await fetch_available_devices(
            mock_hass,
            "http://localhost:8080",
            "+1234567890",
            None,
        )

        assert error is None
        assert len(devices) == 2
        assert devices["contact_+33612345678"] == "John Doe"
        assert devices["group_abc123"] == "Test Group"


@pytest.mark.asyncio
async def test_fetch_available_devices_uses_cache(mock_hass):
    """Test fetch_available_devices returns cached devices without calling API."""
    cached = {"contact_+33612345678": "Cached Contact"}

    with patch(
        "custom_components.signal_gateway.config_flow.discovery.discover_devices",
        new_callable=AsyncMock,
    ) as mock_discover:
        devices, error = await fetch_available_devices(
            mock_hass,
            "http://localhost:8080",
            "+1234567890",
            cached,
        )

        assert error is None
        assert devices == cached
        mock_discover.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_available_devices_connection_error(mock_hass):
    """Test fetch_available_devices handles connection errors."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.discover_devices",
        new_callable=AsyncMock,
    ) as mock_discover:
        mock_discover.side_effect = aiohttp.ClientError("Connection failed")

        devices, error = await fetch_available_devices(
            mock_hass,
            "http://localhost:8080",
            "+1234567890",
            None,
        )

        assert error == "cannot_connect"
        assert devices == {}


@pytest.mark.asyncio
async def test_fetch_available_devices_generic_error(mock_hass):
    """Test fetch_available_devices handles generic errors."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.discover_devices",
        new_callable=AsyncMock,
    ) as mock_discover:
        mock_discover.side_effect = ValueError("Invalid data")

        devices, error = await fetch_available_devices(
            mock_hass,
            "http://localhost:8080",
            "+1234567890",
            None,
        )

        assert error == "unknown"
        assert devices == {}


@pytest.mark.asyncio
async def test_fetch_available_devices_empty_cache_triggers_fetch(mock_hass):
    """Test fetch_available_devices fetches when cache is empty dict."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.discover_devices",
        new_callable=AsyncMock,
    ) as mock_discover:
        mock_discover.return_value = {"contact_+33612345678": "John Doe"}

        devices, error = await fetch_available_devices(
            mock_hass,
            "http://localhost:8080",
            "+1234567890",
            {},  # Empty dict is falsy but should still use cache
        )

        # Empty dict is falsy in Python, so it will trigger a fetch
        # This is expected behavior - empty cache means "no devices found"
        # and we should try again
        assert error is None
        assert len(devices) == 1
        mock_discover.assert_called_once()
