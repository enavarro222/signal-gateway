"""Tests for entity filtering based on approved devices."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.signal_gateway.const import CONF_APPROVED_DEVICES
from custom_components.signal_gateway.data import SignalGatewayEntryData
from custom_components.signal_gateway.const import DOMAIN
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup


def _make_coord(data, entry_id="test_entry_id"):
    """Create a minimal mock coordinator with the given data."""
    coord = MagicMock()
    coord.data = data
    coord.entry_id = entry_id
    return coord


@pytest.fixture
def mock_config_entry_with_approved():
    """Create a mock config entry with approved devices."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_APPROVED_DEVICES: ["contact_+1234567890", "group_group123"],
    }
    return entry


@pytest.fixture
def mock_config_entry_without_approved():
    """Create a mock config entry without approved devices."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {}
    return entry


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


async def test_sensor_platform_filters_by_approved_devices(
    mock_config_entry_with_approved, mock_contacts, mock_groups
):
    """Test sensor platform only creates entities for approved devices."""
    from custom_components.signal_gateway.sensor import async_setup_entry

    mock_client = AsyncMock()
    mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
    mock_client.list_groups = AsyncMock(return_value=mock_groups)

    coordinators = {
        f"contact_{mock_contacts[0].uuid}": _make_coord(mock_contacts[0]),
        f"contact_{mock_contacts[1].uuid}": _make_coord(mock_contacts[1]),
        f"group_{mock_groups[0].internal_id}": _make_coord(mock_groups[0]),
        f"group_{mock_groups[1].internal_id}": _make_coord(mock_groups[1]),
    }

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            mock_config_entry_with_approved.entry_id: SignalGatewayEntryData(
                client=mock_client,
                service_name="test_signal",
                default_recipients=[],
                coordinators=coordinators,
            ),
        },
    }

    mock_add_entities = MagicMock()

    # Call setup
    await async_setup_entry(
        mock_hass, mock_config_entry_with_approved, mock_add_entities
    )

    # Should only create 2 entities (1 contact + 1 group)
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 2
    # Verify the correct entities were created
    assert any(e.contact.number == "+1234567890" for e in entities_added if hasattr(e, "contact"))
    assert any(e.group.id == "group123" for e in entities_added if hasattr(e, "group"))


async def test_sensor_platform_creates_all_when_no_approval_list(
    mock_config_entry_without_approved, mock_contacts, mock_groups
):
    """Test sensor platform creates all entities when no approval list exists."""
    from custom_components.signal_gateway.sensor import async_setup_entry

    mock_client = AsyncMock()
    mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
    mock_client.list_groups = AsyncMock(return_value=mock_groups)

    coordinators = {
        f"contact_{mock_contacts[0].uuid}": _make_coord(mock_contacts[0]),
        f"contact_{mock_contacts[1].uuid}": _make_coord(mock_contacts[1]),
        f"group_{mock_groups[0].internal_id}": _make_coord(mock_groups[0]),
        f"group_{mock_groups[1].internal_id}": _make_coord(mock_groups[1]),
    }

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            mock_config_entry_without_approved.entry_id: SignalGatewayEntryData(
                client=mock_client,
                service_name="test_signal",
                default_recipients=[],
                coordinators=coordinators,
            ),
        },
    }

    mock_add_entities = MagicMock()

    # Call setup
    await async_setup_entry(
        mock_hass, mock_config_entry_without_approved, mock_add_entities
    )

    # Should create all entities (2 contacts + 2 groups)
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 4


async def test_binary_sensor_platform_filters_by_approved_devices(
    mock_contacts, mock_groups
):
    """Test binary_sensor platform only creates entities for approved devices."""
    from custom_components.signal_gateway.binary_sensor import async_setup_entry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_APPROVED_DEVICES: ["contact_+1234567890"],
    }

    mock_client = AsyncMock()
    mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
    mock_client.list_groups = AsyncMock(return_value=mock_groups)

    coordinators = {
        f"contact_{mock_contacts[0].uuid}": _make_coord(mock_contacts[0]),
        f"contact_{mock_contacts[1].uuid}": _make_coord(mock_contacts[1]),
        f"group_{mock_groups[0].internal_id}": _make_coord(mock_groups[0]),
        f"group_{mock_groups[1].internal_id}": _make_coord(mock_groups[1]),
    }

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            entry.entry_id: SignalGatewayEntryData(
                client=mock_client,
                service_name="test_signal",
                default_recipients=[],
                coordinators=coordinators,
            ),
        },
    }

    mock_add_entities = MagicMock()

    # Call setup
    await async_setup_entry(mock_hass, entry, mock_add_entities)

    # Should only create 1 entity (approved contact only)
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 1
    assert entities_added[0].contact.number == "+1234567890"


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_notify_platform_filters_by_approved_devices(
    mock_load_service, mock_set_schema, mock_contacts, mock_groups
):
    """Test notify platform only creates entities for approved devices."""
    from custom_components.signal_gateway.notify import async_setup_entry
    from custom_components.signal_gateway.notify.entities import SignalGroupNotifyEntity

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_APPROVED_DEVICES: ["group_group123", "group_group456"],
    }

    mock_client = AsyncMock()
    mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
    mock_client.list_groups = AsyncMock(return_value=mock_groups)

    coordinators = {
        f"group_{mock_groups[0].internal_id}": _make_coord(mock_groups[0]),
        f"group_{mock_groups[1].internal_id}": _make_coord(mock_groups[1]),
    }

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            entry.entry_id: SignalGatewayEntryData(
                client=mock_client,
                service_name="test_signal",
                default_recipients=[],
                coordinators=coordinators,
            ),
        },
    }
    mock_hass.services = MagicMock()

    mock_add_entities = MagicMock()

    # Call setup
    result = await async_setup_entry(mock_hass, entry, mock_add_entities)

    # Should return True
    assert result is True

    # Should only create 2 entities (both groups)
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 2
    assert all(isinstance(e, SignalGroupNotifyEntity) for e in entities_added)


async def test_empty_approved_devices_list(mock_contacts, mock_groups):
    """Test that empty approved devices list creates no entities."""
    from custom_components.signal_gateway.sensor import async_setup_entry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_APPROVED_DEVICES: [],
    }

    mock_client = AsyncMock()
    mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
    mock_client.list_groups = AsyncMock(return_value=mock_groups)

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            entry.entry_id: SignalGatewayEntryData(
                client=mock_client,
                service_name="test_signal",
                default_recipients=[],
            ),
        },
    }

    mock_add_entities = MagicMock()

    # Call setup
    await async_setup_entry(mock_hass, entry, mock_add_entities)

    # Should create no entities - should have been called with empty list
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 0
