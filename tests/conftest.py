"""Test configuration for Signal Gateway integration."""

import glob as _glob
import os as _os

collect_ignore_glob = [
    _os.path.join(_os.path.dirname(__file__), "._*"),
    _os.path.join(_os.path.dirname(__file__), "**/._*"),
]

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
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.bus.async_listen = MagicMock()
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


@pytest.fixture
def mock_hass_with_bus():
    """Create a mock Home Assistant instance with event bus."""
    from homeassistant.core import HomeAssistant

    hass = MagicMock(spec=HomeAssistant)
    hass.data = {DOMAIN: {}}
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    hass.bus = MagicMock()
    hass.bus.async_listen = MagicMock()
    return hass


@pytest.fixture
def valid_user_input():
    """Create valid user input for config flow."""
    return {
        CONF_NAME: "Test Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
        CONF_WEBSOCKET_ENABLED: True,
        CONF_RECIPIENTS: "",
    }


@pytest.fixture
def mock_contacts():
    """Return mock contacts for discovery."""
    return [
        SignalContact(
            number="+1234567890",
            uuid="uuid-1",
            name="John Doe",
            given_name="John",
            profile_name="John",
            username=None,
            nickname=None,
            profile=None,
            note="",
            color="blue",
            message_expiration="0",
            blocked=False,
        ),
        SignalContact(
            number="+9876543210",
            uuid="uuid-2",
            name="",
            given_name="Jane",
            profile_name="Jane Smith",
            username=None,
            nickname=None,
            profile=None,
            note="",
            color="green",
            message_expiration="0",
            blocked=False,
        ),
    ]


@pytest.fixture
def mock_groups():
    """Return mock groups for discovery."""
    return [
        SignalGroup(
            id="group123",
            internal_id="internal-abc",
            name="Family",
            members=["+1111111111", "+2222222222"],
            blocked=False,
            pending_invites=[],
            pending_requests=[],
            admins=["+1111111111"],
            description="Family group",
        ),
    ]


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    import aiohttp

    return MagicMock(spec=aiohttp.ClientSession)


@pytest.fixture
def mock_contact_coordinator(sample_contact):
    """Create a mock SignalContactCoordinator."""
    from custom_components.signal_gateway.coordinator import SignalContactCoordinator

    coord = MagicMock(spec=SignalContactCoordinator)
    coord.data = sample_contact
    coord.entry_id = "test_entry_id"
    coord.contact_uuid = sample_contact.uuid
    coord.client = AsyncMock()
    coord.client.send_message = AsyncMock(return_value={"success": True})
    coord.device_info = {
        "identifiers": {(DOMAIN, f"test_entry_id_contact_{sample_contact.number}")},
        "name": sample_contact.name or sample_contact.number,
        "manufacturer": "Signal Messenger",
        "model": "Contact",
    }
    return coord


@pytest.fixture
def mock_group_coordinator(sample_group):
    """Create a mock SignalGroupCoordinator."""
    from custom_components.signal_gateway.coordinator import SignalGroupCoordinator

    coord = MagicMock(spec=SignalGroupCoordinator)
    coord.data = sample_group
    coord.entry_id = "test_entry_id"
    coord.group_id = sample_group.id
    coord.client = AsyncMock()
    coord.client.send_message = AsyncMock(return_value={"success": True})
    coord.device_info = {
        "identifiers": {
            (DOMAIN, f"test_entry_id_group_{sample_group.id}"),
            (DOMAIN, f"test_entry_id_group-internal_{sample_group.internal_id}"),
        },
        "name": sample_group.name,
        "manufacturer": "Signal Messenger",
        "model": "Group",
    }
    return coord
