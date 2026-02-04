"""Unit tests for Signal Gateway notify entities setup."""

from unittest.mock import AsyncMock

import pytest

from custom_components.signal_gateway.notify.entities import (
    SignalContactNotifyEntity,
    SignalGroupNotifyEntity,
    async_setup_entry,
)
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup


async def test_async_setup_entry_with_contacts_and_groups(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry successfully creates entities for contacts and groups."""
    from custom_components.signal_gateway.const import DOMAIN

    # Setup client with contacts and groups
    contacts = [
        SignalContact(number="+1111111111", uuid="uuid1", name="Alice"),
        SignalContact(number="+2222222222", uuid="uuid2", name="Bob"),
    ]
    groups = [
        SignalGroup(
            id="group1", name="Family", internal_id="int1", members=["+1111111111"]
        ),
        SignalGroup(
            id="group2", name="Work", internal_id="int2", members=["+2222222222"]
        ),
    ]

    mock_signal_client.list_contacts = AsyncMock(return_value=contacts)
    mock_signal_client.list_groups = AsyncMock(return_value=groups)

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    # Call async_setup_entry
    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    # Verify client methods were called
    mock_signal_client.list_contacts.assert_called_once()
    mock_signal_client.list_groups.assert_called_once()

    # Verify entities were added
    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]

    # Should have 2 contact entities + 2 group entities = 4 total
    assert len(entities) == 4

    # Verify entity types
    contact_entities = [e for e in entities if isinstance(e, SignalContactNotifyEntity)]
    group_entities = [e for e in entities if isinstance(e, SignalGroupNotifyEntity)]

    assert len(contact_entities) == 2
    assert len(group_entities) == 2

    # Verify entity properties
    assert contact_entities[0]._contact.name == "Alice"
    assert contact_entities[1]._contact.name == "Bob"
    assert group_entities[0]._group.name == "Family"
    assert group_entities[1]._group.name == "Work"


async def test_async_setup_entry_empty_contacts_and_groups(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry when no contacts or groups exist."""
    from custom_components.signal_gateway.const import DOMAIN

    mock_signal_client.list_contacts = AsyncMock(return_value=[])
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    # Verify empty list was added
    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 0


async def test_async_setup_entry_contacts_only(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry with only contacts (no groups)."""
    from custom_components.signal_gateway.const import DOMAIN

    contacts = [
        SignalContact(number="+1111111111", uuid="uuid1", name="Alice"),
    ]

    mock_signal_client.list_contacts = AsyncMock(return_value=contacts)
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], SignalContactNotifyEntity)


async def test_async_setup_entry_groups_only(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry with only groups (no contacts)."""
    from custom_components.signal_gateway.const import DOMAIN

    groups = [
        SignalGroup(
            id="group1", name="Family", internal_id="int1", members=["+1111111111"]
        ),
    ]

    mock_signal_client.list_contacts = AsyncMock(return_value=[])
    mock_signal_client.list_groups = AsyncMock(return_value=groups)

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], SignalGroupNotifyEntity)


async def test_async_setup_entry_contact_fetch_failure(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry handles contact fetch failures gracefully."""
    from custom_components.signal_gateway.const import DOMAIN

    # Contacts fail, but groups succeed
    mock_signal_client.list_contacts = AsyncMock(side_effect=Exception("API Error"))
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    # Should still call async_add_entities with empty list
    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 0


async def test_async_setup_entry_group_fetch_failure(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry handles group fetch failures gracefully."""
    from custom_components.signal_gateway.const import DOMAIN

    contacts = [
        SignalContact(number="+1111111111", uuid="uuid1", name="Alice"),
    ]

    # Contacts succeed, but groups fail
    mock_signal_client.list_contacts = AsyncMock(return_value=contacts)
    mock_signal_client.list_groups = AsyncMock(side_effect=Exception("Group API Error"))

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    # Contact entities are created before the group fetch fails
    # So we still get the contact entities
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], SignalContactNotifyEntity)


async def test_async_setup_entry_both_fetch_failures(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test async_setup_entry when both contacts and groups fetch fail."""
    from custom_components.signal_gateway.const import DOMAIN

    mock_signal_client.list_contacts = AsyncMock(
        side_effect=Exception("Contacts API Error")
    )
    mock_signal_client.list_groups = AsyncMock(
        side_effect=Exception("Groups API Error")
    )

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    # Should still call async_add_entities with empty list
    mock_add_entities.assert_called_once()
    entities = mock_add_entities.call_args[0][0]
    assert len(entities) == 0


async def test_async_setup_entry_entity_unique_ids(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test that async_setup_entry creates entities with correct unique IDs."""
    from custom_components.signal_gateway.const import DOMAIN

    contacts = [
        SignalContact(number="+1234567890", uuid="uuid1", name="Test User"),
    ]
    groups = [
        SignalGroup(id="group-abc", name="Test Group", internal_id="int1", members=[]),
    ]

    mock_signal_client.list_contacts = AsyncMock(return_value=contacts)
    mock_signal_client.list_groups = AsyncMock(return_value=groups)

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]

    # Verify unique IDs follow expected pattern
    contact_entity = next(
        e for e in entities if isinstance(e, SignalContactNotifyEntity)
    )
    group_entity = next(e for e in entities if isinstance(e, SignalGroupNotifyEntity))

    assert (
        contact_entity.unique_id == f"{mock_entry.entry_id}_contact_+1234567890_notify"
    )
    assert group_entity.unique_id == f"{mock_entry.entry_id}_group_group-abc_notify"


async def test_async_setup_entry_entity_names(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test that async_setup_entry creates entities with correct names."""
    from custom_components.signal_gateway.const import DOMAIN

    contacts = [
        SignalContact(number="+1234567890", uuid="uuid1", name="John Smith"),
    ]
    groups = [
        SignalGroup(id="group-abc", name="My Team", internal_id="int1", members=[]),
    ]

    mock_signal_client.list_contacts = AsyncMock(return_value=contacts)
    mock_signal_client.list_groups = AsyncMock(return_value=groups)

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    entities = mock_add_entities.call_args[0][0]

    # All entities should have "Notify" as their name attribute
    for entity in entities:
        assert entity.name == "Notify"

    # But their display names (from device info) should reflect contact/group
    contact_entity = next(
        e for e in entities if isinstance(e, SignalContactNotifyEntity)
    )
    group_entity = next(e for e in entities if isinstance(e, SignalGroupNotifyEntity))

    assert contact_entity._display_name == "John Smith"
    assert group_entity._display_name == "My Team"


async def test_async_setup_entry_update_before_add_flag(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test that async_setup_entry calls async_add_entities with update_before_add=True."""
    from custom_components.signal_gateway.const import DOMAIN

    contacts = [SignalContact(number="+1111111111", uuid="uuid1", name="Alice")]
    mock_signal_client.list_contacts = AsyncMock(return_value=contacts)
    mock_signal_client.list_groups = AsyncMock(return_value=[])

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {"client": mock_signal_client}

    await async_setup_entry(mock_hass, mock_entry, mock_add_entities)

    # Verify the second argument (update_before_add) is True
    call_args = mock_add_entities.call_args
    assert call_args[0][1] is True  # Second positional argument
