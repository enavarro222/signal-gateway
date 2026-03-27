"""End-to-end tests for device discovery and entity creation."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import AsyncMock, patch, MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME

from custom_components.signal_gateway.const import (
    DOMAIN,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_PHONE_NUMBER,
    CONF_APPROVED_DEVICES,
    CONF_WEBSOCKET_ENABLED,
)
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup


@pytest.fixture
def mock_contacts():
    """Mock list of contacts."""
    return [
        SignalContact(
            number="+33612345678",
            name="Alice",
            uuid="uuid-alice",
        ),
        SignalContact(
            number="+33687654321",
            name="Bob",
            uuid="uuid-bob",
        ),
    ]


@pytest.fixture
def mock_groups():
    """Mock list of groups."""
    return [
        SignalGroup(
            id="group-id-1",
            name="Family",
            internal_id="internal-group-1",
            description="Family group",
            members=["+33612345678", "+33687654321"],
        ),
        SignalGroup(
            id="group-id-2",
            name="Friends",
            internal_id="internal-group-2",
            description="Friends group",
            members=["+33612345678"],
        ),
    ]


@pytest.mark.asyncio
async def test_e2e_full_setup_with_device_approval(
    hass: HomeAssistant, mock_contacts, mock_groups
):
    """Test complete flow: setup with device approval creates entities."""
    contact_lookup = {c.uuid: c for c in mock_contacts}
    group_lookup = {g.id: g for g in mock_groups}

    with patch("custom_components.signal_gateway.SignalClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_client.list_groups = AsyncMock(return_value=mock_groups)
        mock_client.get_contact = AsyncMock(
            side_effect=lambda uuid: contact_lookup.get(uuid)
        )
        mock_client.get_group = AsyncMock(
            side_effect=lambda group_id: group_lookup.get(group_id)
        )
        mock_client.send_message = AsyncMock(return_value={"timestamp": 123456})
        mock_client.start_listening = AsyncMock()
        mock_client.stop_listening = AsyncMock()
        mock_client.set_message_handler = MagicMock()
        mock_client_class.return_value = mock_client

        # Create config entry with approved devices
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: "test_gateway",
                CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
                CONF_PHONE_NUMBER: "+33600000000",
                CONF_WEBSOCKET_ENABLED: False,
                CONF_APPROVED_DEVICES: [
                    "contact_+33612345678",  # Alice
                    "group_group-id-1",  # Family
                ],
            },
            entry_id="test_entry_id",
            unique_id="test_gateway",
        )
        config_entry.add_to_hass(hass)

        # Setup integration
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # Verify entities were created (2 approved devices × 3 entity types = 6 entities)
        # Alice contact: sensor, binary_sensor, notify
        assert hass.states.get("sensor.alice_info") is not None
        assert hass.states.get("binary_sensor.alice_is_writing") is not None
        assert hass.states.get("notify.alice_notify") is not None

        # Family group: sensor, binary_sensor, notify
        assert hass.states.get("sensor.family_info") is not None
        assert hass.states.get("binary_sensor.family_is_writing") is not None
        assert hass.states.get("notify.family_notify") is not None

        # Bob (not approved) should NOT have entities
        assert hass.states.get("sensor.bob_info") is None
        assert hass.states.get("binary_sensor.bob_is_writing") is None
        assert hass.states.get("notify.bob_notify") is None

        # Friends group (not approved) should NOT have entities
        assert hass.states.get("sensor.friends_info") is None
        assert hass.states.get("binary_sensor.friends_is_writing") is None
        assert hass.states.get("notify.friends_notify") is None

        # Legacy notify service should still exist
        assert hass.services.has_service("notify", "test_gateway")


@pytest.mark.asyncio
async def test_e2e_setup_without_approved_devices(
    hass: HomeAssistant, mock_contacts, mock_groups
):
    """Test setup without approved devices creates no entities (backward compat)."""
    contact_lookup = {c.uuid: c for c in mock_contacts}
    group_lookup = {g.id: g for g in mock_groups}

    with patch("custom_components.signal_gateway.SignalClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_client.list_groups = AsyncMock(return_value=mock_groups)
        mock_client.get_contact = AsyncMock(
            side_effect=lambda uuid: contact_lookup.get(uuid)
        )
        mock_client.get_group = AsyncMock(
            side_effect=lambda group_id: group_lookup.get(group_id)
        )
        mock_client.send_message = AsyncMock(return_value={"timestamp": 123456})
        mock_client.start_listening = AsyncMock()
        mock_client.stop_listening = AsyncMock()
        mock_client.set_message_handler = MagicMock()
        mock_client_class.return_value = mock_client

        # Create config entry WITHOUT approved_devices (old config)
        config_entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_NAME: "test_gateway_old",
                CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
                CONF_PHONE_NUMBER: "+33600000000",
                CONF_WEBSOCKET_ENABLED: False,
                # No CONF_APPROVED_DEVICES - backward compatibility
            },
            entry_id="test_entry_old",
            unique_id="test_gateway_old",
        )
        config_entry.add_to_hass(hass)

        # Setup integration
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        # With no approved devices list, ALL devices should be created (backward compat)
        # Alice contact
        assert hass.states.get("sensor.alice_info") is not None
        assert hass.states.get("binary_sensor.alice_is_writing") is not None
        assert hass.states.get("notify.alice_notify") is not None

        # Bob contact
        assert hass.states.get("sensor.bob_info") is not None
        assert hass.states.get("binary_sensor.bob_is_writing") is not None
        assert hass.states.get("notify.bob_notify") is not None

        # Family group
        assert hass.states.get("sensor.family_info") is not None
        assert hass.states.get("binary_sensor.family_is_writing") is not None
        assert hass.states.get("notify.family_notify") is not None

        # Friends group
        assert hass.states.get("sensor.friends_info") is not None
        assert hass.states.get("binary_sensor.friends_is_writing") is not None
        assert hass.states.get("notify.friends_notify") is not None
