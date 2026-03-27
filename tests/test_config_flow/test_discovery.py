"""Tests for device discovery in config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import CONF_NAME

from custom_components.signal_gateway.config_flow import SignalGatewayConfigFlow
from custom_components.signal_gateway.const import (
    CONF_APPROVED_DEVICES,
    CONF_PHONE_NUMBER,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
)
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup


@pytest.fixture
def mock_contacts():
    """Return mock contacts."""
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
            profile_name="Jane",
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
    """Return mock groups."""
    from custom_components.signal_gateway.signal.models import GroupPermissions

    return [
        SignalGroup(
            id="group123",
            name="Family Group",
            internal_id="internal_group123",
            members=["+1234567890", "+9876543210"],
            admins=["+1234567890"],
            description="Family chat",
            invite_link="",
            blocked=False,
            pending_invites=[],
            pending_requests=[],
            permissions=GroupPermissions(
                add_members="every-member",
                edit_group="every-member",
                send_messages="every-member",
            ),
        ),
        SignalGroup(
            id="group456",
            name="Work Group",
            internal_id="internal_group456",
            members=["+1234567890"],
            admins=["+1234567890"],
            description="Work chat",
            invite_link="",
            blocked=False,
            pending_invites=[],
            pending_requests=[],
            permissions=GroupPermissions(
                add_members="only-admins",
                edit_group="only-admins",
                send_messages="every-member",
            ),
        ),
    ]


async def test_discovery_step_with_contacts_and_groups(
    hass, mock_contacts, mock_groups
):
    """Test discovery step with contacts and groups."""
    flow = SignalGatewayConfigFlow()
    flow.hass = hass

    # Set up initial user input
    flow._user_input = {
        CONF_NAME: "Test Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1111111111",
        CONF_WEBSOCKET_ENABLED: True,
    }

    # Mock SignalClient
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_instance.list_groups = AsyncMock(return_value=mock_groups)
        mock_client.return_value = mock_instance

        # Call discovery step without user input (should show form)
        result = await flow.async_step_discovery()

        assert result["type"] == "form"
        assert result["step_id"] == "discovery"
        assert "approved_devices" in result["data_schema"].schema
        assert result["description_placeholders"]["device_count"] == "4"


async def test_discovery_step_user_selection(hass, mock_contacts, mock_groups):
    """Test discovery step with user device selection."""
    flow = SignalGatewayConfigFlow()
    flow.hass = hass

    # Set up initial user input
    flow._user_input = {
        CONF_NAME: "Test Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1111111111",
        CONF_WEBSOCKET_ENABLED: True,
    }

    # Mock SignalClient
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_instance.list_groups = AsyncMock(return_value=mock_groups)
        mock_client.return_value = mock_instance

        # First call to populate available devices
        await flow.async_step_discovery()

        # User selects specific devices
        user_selection = {
            CONF_APPROVED_DEVICES: ["contact_+1234567890", "group_group123"]
        }

        # Second call with user selection
        result = await flow.async_step_discovery(user_selection)

        assert result["type"] == "create_entry"
        assert result["title"] == "Test Gateway"
        assert CONF_APPROVED_DEVICES in result["data"]
        assert "contact_+1234567890" in result["data"][CONF_APPROVED_DEVICES]
        assert "group_group123" in result["data"][CONF_APPROVED_DEVICES]
        assert len(result["data"][CONF_APPROVED_DEVICES]) == 2


async def test_discovery_step_no_devices(hass):
    """Test discovery step when no devices are found."""
    flow = SignalGatewayConfigFlow()
    flow.hass = hass

    # Set up initial user input
    flow._user_input = {
        CONF_NAME: "Test Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1111111111",
        CONF_WEBSOCKET_ENABLED: True,
    }

    # Mock SignalClient returning no devices
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=[])
        mock_instance.list_groups = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        # Call discovery step
        result = await flow.async_step_discovery()

        # Should create entry with empty approved_devices
        assert result["type"] == "create_entry"
        assert result["title"] == "Test Gateway"
        assert result["data"][CONF_APPROVED_DEVICES] == []


async def test_discovery_step_api_error(hass):
    """Test discovery step when API connection fails."""
    flow = SignalGatewayConfigFlow()
    flow.hass = hass

    # Set up initial user input
    flow._user_input = {
        CONF_NAME: "Test Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1111111111",
        CONF_WEBSOCKET_ENABLED: True,
    }

    # Mock SignalClient raising an exception
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(side_effect=Exception("API Error"))
        mock_client.return_value = mock_instance

        # Call discovery step
        result = await flow.async_step_discovery()

        # Should create entry with empty approved_devices and show error
        assert result["type"] == "create_entry"
        assert result["data"][CONF_APPROVED_DEVICES] == []


async def test_discovery_step_select_all_devices(hass, mock_contacts, mock_groups):
    """Test discovery step when user selects all devices."""
    flow = SignalGatewayConfigFlow()
    flow.hass = hass

    # Set up initial user input
    flow._user_input = {
        CONF_NAME: "Test Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1111111111",
        CONF_WEBSOCKET_ENABLED: True,
    }

    # Mock SignalClient
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_instance.list_groups = AsyncMock(return_value=mock_groups)
        mock_client.return_value = mock_instance

        # First call to populate available devices
        await flow.async_step_discovery()

        # User selects all devices
        user_selection = {
            CONF_APPROVED_DEVICES: [
                "contact_+1234567890",
                "contact_+9876543210",
                "group_group123",
                "group_group456",
            ]
        }

        # Second call with user selection
        result = await flow.async_step_discovery(user_selection)

        assert result["type"] == "create_entry"
        assert len(result["data"][CONF_APPROVED_DEVICES]) == 4
