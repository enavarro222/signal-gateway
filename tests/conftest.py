"""Test configuration for Signal Gateway integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.signal_gateway.const import (
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
)
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in Home Assistant tests.

    This fixture is automatically applied to all tests (autouse=True) and enables
    Home Assistant to load custom components from custom_components/ directory.

    Required for:
    - End-to-end tests using the real 'hass' fixture
    - Tests that need to setup config entries
    - Any test that loads the signal_gateway integration

    Provided by pytest-homeassistant-custom-component package.
    """
    yield


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


# Common fixtures for testing


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {DOMAIN: {}, "avatar_secret": "test_secret_key_12345"}
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.config.path.return_value = "secret_path"
    hass.http = MagicMock()
    return hass


@pytest.fixture
def mock_signal_client():
    """Create a mock Signal client."""
    client = AsyncMock()
    client.send_message = AsyncMock(return_value={"success": True})
    client.list_contacts = AsyncMock(return_value=[])
    client.list_groups = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_123"
    entry.data = {}
    return entry


@pytest.fixture
def mock_add_entities():
    """Create a mock async_add_entities callback."""
    return MagicMock()


@pytest.fixture
def sample_contact():
    """Create a sample contact."""
    return SignalContact(
        number="+1234567890",
        uuid="test-uuid",
        name="John Doe",
    )


@pytest.fixture
def sample_group():
    """Create a sample group."""
    return SignalGroup(
        id="group-id-123",
        name="Test Group",
        internal_id="internal-123",
        members=["+1234567890"],
    )
