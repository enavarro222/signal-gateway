"""Unit tests for Signal Gateway notify platform setup (async_setup_entry)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.signal_gateway.notify import async_setup_entry
from custom_components.signal_gateway.notify.entities import (
    SignalContactNotifyEntity,
    SignalGroupNotifyEntity,
)
from custom_components.signal_gateway.coordinator import (
    SignalContactCoordinator,
    SignalGroupCoordinator,
)
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup
from custom_components.signal_gateway.data import SignalGatewayEntryData
from custom_components.signal_gateway.const import DOMAIN


def _make_contact_coordinator(entry_id, contact):
    coord = MagicMock(spec=SignalContactCoordinator)
    coord.data = contact
    coord.entry_id = entry_id
    coord.contact_uuid = contact.uuid
    coord.client = AsyncMock()
    return coord


def _make_group_coordinator(entry_id, group):
    coord = MagicMock(spec=SignalGroupCoordinator)
    coord.data = group
    coord.entry_id = entry_id
    coord.group_id = group.id
    coord.client = AsyncMock()
    return coord


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_with_contacts_and_groups(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry successfully creates entities for contacts and groups."""
    contacts = [
        SignalContact(number="+1111111111", uuid="uuid1", name="Alice"),
        SignalContact(number="+2222222222", uuid="uuid2", name="Bob"),
    ]
    groups = [
        SignalGroup(id="group1", name="Family", internal_id="int1", members=["+1111111111"]),
        SignalGroup(id="group2", name="Work", internal_id="int2", members=["+2222222222"]),
    ]

    mock_signal_client.list_contacts = AsyncMock(return_value=contacts)
    mock_signal_client.list_groups = AsyncMock(return_value=groups)

    coordinators = {
        "contact_uuid1": _make_contact_coordinator(mock_entry.entry_id, contacts[0]),
        "contact_uuid2": _make_contact_coordinator(mock_entry.entry_id, contacts[1]),
        "group_int1": _make_group_coordinator(mock_entry.entry_id, groups[0]),
        "group_int2": _make_group_coordinator(mock_entry.entry_id, groups[1]),
    }

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators=coordinators,
    )

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    mock_signal_client.list_contacts.assert_called_once()
    mock_signal_client.list_groups.assert_called_once()
    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]

    assert len(entities) == 4

    contact_entities = [e for e in entities if isinstance(e, SignalContactNotifyEntity)]
    group_entities = [e for e in entities if isinstance(e, SignalGroupNotifyEntity)]

    assert len(contact_entities) == 2
    assert len(group_entities) == 2

    assert contact_entities[0].contact.name == "Alice"
    assert contact_entities[1].contact.name == "Bob"
    assert group_entities[0].group.name == "Family"
    assert group_entities[1].group.name == "Work"


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_empty_contacts_and_groups(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry when no contacts or groups exist."""
    mock_signal_client.list_contacts = AsyncMock(return_value=[])
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
    )

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 0


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_contacts_only(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry with only contacts (no groups)."""
    contact = SignalContact(number="+1111111111", uuid="uuid1", name="Alice")
    mock_signal_client.list_contacts = AsyncMock(return_value=[contact])
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    coordinators = {
        "contact_uuid1": _make_contact_coordinator(mock_entry.entry_id, contact),
    }

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators=coordinators,
    )

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], SignalContactNotifyEntity)


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_groups_only(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry with only groups (no contacts)."""
    group = SignalGroup(id="group1", name="Family", internal_id="int1", members=["+1111111111"])
    mock_signal_client.list_contacts = AsyncMock(return_value=[])
    mock_signal_client.list_groups = AsyncMock(return_value=[group])

    coordinators = {
        "group_int1": _make_group_coordinator(mock_entry.entry_id, group),
    }

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators=coordinators,
    )

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], SignalGroupNotifyEntity)


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_fetch_failure(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry handles API failures gracefully (legacy service still registers)."""
    mock_signal_client.list_contacts = AsyncMock(side_effect=Exception("API Error"))
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
    )

    # Should not raise, legacy service still registered
    result = await async_setup_entry(mock_hass, mock_entry, mock_add_entities)
    assert result is True

    # async_add_entities not called when fetch fails
    mock_add_entities.assert_not_called()


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_both_fetch_failures(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry when both contacts and groups fetch fail."""
    mock_signal_client.list_contacts = AsyncMock(side_effect=Exception("Contacts API Error"))
    mock_signal_client.list_groups = AsyncMock(side_effect=Exception("Groups API Error"))

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
    )

    result = await async_setup_entry(mock_hass, mock_entry, mock_add_entities)
    assert result is True
    mock_add_entities.assert_not_called()


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_entity_unique_ids(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test that async_setup_entry creates entities with correct unique IDs."""
    contact = SignalContact(number="+1234567890", uuid="uuid1", name="Test User")
    group = SignalGroup(id="group-abc", name="Test Group", internal_id="int1", members=[])

    mock_signal_client.list_contacts = AsyncMock(return_value=[contact])
    mock_signal_client.list_groups = AsyncMock(return_value=[group])

    coordinators = {
        "contact_uuid1": _make_contact_coordinator(mock_entry.entry_id, contact),
        "group_int1": _make_group_coordinator(mock_entry.entry_id, group),
    }

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators=coordinators,
    )

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]

    contact_entity = next(e for e in entities if isinstance(e, SignalContactNotifyEntity))
    group_entity = next(e for e in entities if isinstance(e, SignalGroupNotifyEntity))

    # Contact unique_id now uses uuid (not phone number)
    assert contact_entity.unique_id == f"{mock_entry.entry_id}_contact_uuid1_notify"
    assert group_entity.unique_id == f"{mock_entry.entry_id}_group_group-abc_notify"


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_entity_names(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test that async_setup_entry creates entities with correct names."""
    contact = SignalContact(number="+1234567890", uuid="uuid1", name="John Smith")
    group = SignalGroup(id="group-abc", name="My Team", internal_id="int1", members=[])

    mock_signal_client.list_contacts = AsyncMock(return_value=[contact])
    mock_signal_client.list_groups = AsyncMock(return_value=[group])

    coordinators = {
        "contact_uuid1": _make_contact_coordinator(mock_entry.entry_id, contact),
        "group_int1": _make_group_coordinator(mock_entry.entry_id, group),
    }

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators=coordinators,
    )

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]

    for entity in entities:
        assert entity.name == "Notify"

    contact_entity = next(e for e in entities if isinstance(e, SignalContactNotifyEntity))
    group_entity = next(e for e in entities if isinstance(e, SignalGroupNotifyEntity))

    assert contact_entity.contact.display_name == "John Smith"
    assert group_entity.group.name == "My Team"


@patch("custom_components.signal_gateway.notify.async_set_service_schema")
@patch("custom_components.signal_gateway.notify.async_load_notify_service")
async def test_async_setup_entry_update_before_add_flag(
    mock_load_service, mock_set_schema,
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test that async_setup_entry calls async_add_entities with update_before_add=True."""
    contact = SignalContact(number="+1111111111", uuid="uuid1", name="Alice")
    mock_signal_client.list_contacts = AsyncMock(return_value=[contact])
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    coordinators = {
        "contact_uuid1": _make_contact_coordinator(mock_entry.entry_id, contact),
    }

    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators=coordinators,
    )

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    call_args = mock_add_entities.call_args
    assert call_args[0][1] is True
