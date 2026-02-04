"""Tests for entity filtering based on approved devices."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry

from custom_components.signal_gateway.const import CONF_APPROVED_DEVICES, DOMAIN
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup


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

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            mock_config_entry_with_approved.entry_id: {"client": mock_client},
        },
    }

    # Mock async_add_entities with AsyncMock
    mock_add_entities = AsyncMock()

    # Call setup
    await async_setup_entry(
        mock_hass, mock_config_entry_with_approved, mock_add_entities
    )

    # Should only create 2 entities (1 contact + 1 group)
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 2
    # Verify the correct entities were created
    assert any(
        hasattr(e, "_contact") and e._contact.number == "+1234567890"
        for e in entities_added
    )
    assert any(
        hasattr(e, "_group") and e._group.id == "group123" for e in entities_added
    )


async def test_sensor_platform_creates_all_when_no_approval_list(
    mock_config_entry_without_approved, mock_contacts, mock_groups
):
    """Test sensor platform creates all entities when no approval list exists."""
    from custom_components.signal_gateway.sensor import async_setup_entry

    mock_client = AsyncMock()
    mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
    mock_client.list_groups = AsyncMock(return_value=mock_groups)

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            mock_config_entry_without_approved.entry_id: {"client": mock_client},
        },
    }

    # Mock async_add_entities with AsyncMock
    mock_add_entities = AsyncMock()

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

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            entry.entry_id: {"client": mock_client},
        },
    }

    # Mock async_add_entities with AsyncMock
    mock_add_entities = AsyncMock()

    # Call setup
    await async_setup_entry(mock_hass, entry, mock_add_entities)

    # Should only create 1 entity
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 1
    assert hasattr(entities_added[0], "_contact")
    assert entities_added[0]._contact.number == "+1234567890"


async def test_notify_platform_filters_by_approved_devices(mock_contacts, mock_groups):
    """Test notify platform only creates entities for approved devices."""
    from custom_components.signal_gateway.notify import async_setup_entry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.data = {
        CONF_APPROVED_DEVICES: ["group_group123", "group_group456"],
    }

    mock_client = AsyncMock()
    mock_client.list_contacts = AsyncMock(return_value=mock_contacts)
    mock_client.list_groups = AsyncMock(return_value=mock_groups)

    mock_hass = MagicMock()
    mock_hass.data = {
        DOMAIN: {
            entry.entry_id: {
                "client": mock_client,
                "service_name": "test_signal",
                "default_recipients": [],
            },
        },
    }
    mock_hass.services = MagicMock()

    # Mock async_add_entities with AsyncMock
    mock_add_entities = AsyncMock()

    # Call setup
    result = await async_setup_entry(mock_hass, entry, mock_add_entities)

    # Should return True
    assert result is True

    # Should only create 2 entities (both groups)
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 2
    assert all(hasattr(e, "_group") for e in entities_added)


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
            entry.entry_id: {"client": mock_client},
        },
    }

    # Mock async_add_entities with AsyncMock
    mock_add_entities = AsyncMock()

    # Call setup
    await async_setup_entry(mock_hass, entry, mock_add_entities)

    # Should create no entities - should have been called with empty list
    mock_add_entities.assert_called_once()
    entities_added = mock_add_entities.call_args[0][0]
    assert len(entities_added) == 0
