"""Shared fixtures for __init__.py tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from custom_components.signal_gateway.const import (
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
)


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass


@pytest.fixture
def mock_entry():
    """Create a mock ConfigEntry with full configuration."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
        CONF_NAME: "Test Signal",
        CONF_RECIPIENTS: "+9876543210, +5551234567",
        CONF_WEBSOCKET_ENABLED: True,
    }
    entry.add_update_listener = MagicMock()
    return entry


@pytest.fixture
def mock_entry_minimal():
    """Create a minimal mock ConfigEntry for unload tests."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    return entry
