"""Unit tests for Signal Gateway notify entities."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.signal_gateway.notify.entities import (
    SignalContactNotifyEntity,
    SignalGroupNotifyEntity,
)
from custom_components.signal_gateway.coordinator import (
    SignalContactCoordinator,
    SignalGroupCoordinator,
)
from custom_components.signal_gateway.const import DOMAIN


# Test SignalContactNotifyEntity


def test_contact_notify_entity_initialization(mock_contact_coordinator, sample_contact):
    """Test contact notify entity initialization."""
    entity = SignalContactNotifyEntity(mock_contact_coordinator)

    assert entity.contact == sample_contact
    assert entity.coordinator.entry_id == "test_entry_id"
    assert entity.name == "Notify"
    # unique_id now uses uuid (not phone number)
    assert entity.unique_id == f"test_entry_id_contact_{sample_contact.uuid}_notify"
    assert entity.icon == "mdi:message-text"


async def test_contact_notify_entity_send_message(mock_contact_coordinator, sample_contact):
    """Test sending message via contact notify entity."""
    entity = SignalContactNotifyEntity(mock_contact_coordinator)

    await entity.async_send_message(message="Hello", title="Greeting")

    mock_contact_coordinator.client.send_message.assert_called_once_with(
        target=sample_contact.number,
        message="Greeting\n\nHello",
        base64_attachments=[],
    )


async def test_contact_notify_entity_send_message_no_title(
    mock_contact_coordinator, sample_contact
):
    """Test sending message without title."""
    entity = SignalContactNotifyEntity(mock_contact_coordinator)

    await entity.async_send_message(message="Hello")

    mock_contact_coordinator.client.send_message.assert_called_once_with(
        target=sample_contact.number,
        message="Hello",
        base64_attachments=[],
    )


async def test_contact_notify_entity_send_message_error(
    mock_contact_coordinator, sample_contact
):
    """Test error handling when sending message."""
    mock_contact_coordinator.client.send_message.side_effect = Exception("Send failed")
    entity = SignalContactNotifyEntity(mock_contact_coordinator)

    with pytest.raises(Exception, match="Send failed"):
        await entity.async_send_message(message="Hello")


def test_contact_notify_entity_device_info(mock_contact_coordinator, sample_contact):
    """Test contact notify entity device info delegates to coordinator."""
    entity = SignalContactNotifyEntity(mock_contact_coordinator)
    device_info = entity.device_info

    assert (DOMAIN, f"test_entry_id_contact_{sample_contact.number}") in device_info["identifiers"]
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Contact"


# Test SignalGroupNotifyEntity


def test_group_notify_entity_initialization(mock_group_coordinator, sample_group):
    """Test group notify entity initialization."""
    entity = SignalGroupNotifyEntity(mock_group_coordinator)

    assert entity.group == sample_group
    assert entity.coordinator.entry_id == "test_entry_id"
    assert entity.name == "Notify"
    assert entity.unique_id == f"test_entry_id_group_{sample_group.id}_notify"
    assert entity.icon == "mdi:message-text"


async def test_group_notify_entity_send_message(mock_group_coordinator, sample_group):
    """Test sending message via group notify entity."""
    entity = SignalGroupNotifyEntity(mock_group_coordinator)

    await entity.async_send_message(message="Hello everyone", title="Announcement")

    mock_group_coordinator.client.send_message.assert_called_once_with(
        target=sample_group.id,
        message="Announcement\n\nHello everyone",
        base64_attachments=[],
    )


async def test_group_notify_entity_send_message_no_title(mock_group_coordinator, sample_group):
    """Test sending message without title."""
    entity = SignalGroupNotifyEntity(mock_group_coordinator)

    await entity.async_send_message(message="Hello everyone")

    mock_group_coordinator.client.send_message.assert_called_once_with(
        target=sample_group.id,
        message="Hello everyone",
        base64_attachments=[],
    )


async def test_group_notify_entity_send_message_error(mock_group_coordinator, sample_group):
    """Test error handling when sending message."""
    mock_group_coordinator.client.send_message.side_effect = Exception("Send failed")
    entity = SignalGroupNotifyEntity(mock_group_coordinator)

    with pytest.raises(Exception, match="Send failed"):
        await entity.async_send_message(message="Hello")


def test_group_notify_entity_device_info(mock_group_coordinator, sample_group):
    """Test group notify entity device info delegates to coordinator."""
    entity = SignalGroupNotifyEntity(mock_group_coordinator)
    device_info = entity.device_info

    assert (DOMAIN, f"test_entry_id_group_{sample_group.id}") in device_info["identifiers"]
    assert (DOMAIN, f"test_entry_id_group-internal_{sample_group.internal_id}") in device_info["identifiers"]
    assert device_info["name"] == sample_group.name
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Group"
