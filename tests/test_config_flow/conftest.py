"""Shared fixtures for config_flow tests."""

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME

from custom_components.signal_gateway.const import (
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
)


@pytest.fixture
def mock_config_entry():
    """Create a mock ConfigEntry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test Signal",
        data={
            CONF_NAME: "Test Signal",
            CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
            CONF_PHONE_NUMBER: "+1234567890",
            CONF_WEBSOCKET_ENABLED: True,
            CONF_RECIPIENTS: "+9876543210",
        },
        source="user",
        entry_id="test_entry_id",
        unique_id="test_unique_id",
        discovery_keys={},
        options={},
        subentries_data={},
    )


@pytest.fixture
def valid_user_input():
    """Create valid user input data."""
    return {
        CONF_NAME: "My Signal",
        CONF_SIGNAL_CLI_REST_API_URL: "http://192.168.1.100:8080",
        CONF_PHONE_NUMBER: "+1234567890",
        CONF_WEBSOCKET_ENABLED: True,
        CONF_RECIPIENTS: "+9876543210, +5551234567",
    }
