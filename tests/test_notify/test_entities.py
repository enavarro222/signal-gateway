"""Unit tests for Signal Gateway notify entities."""

import pytest

from custom_components.signal_gateway.notify.entities import (
    SignalContactNotifyEntity,
    SignalGroupNotifyEntity,
)


# Test SignalContactNotifyEntity


def test_contact_notify_entity_initialization(mock_signal_client, sample_contact):
    """Test contact notify entity initialization."""
    entity = SignalContactNotifyEntity(mock_signal_client, sample_contact, "test_entry")

    assert entity._contact == sample_contact
    assert entity._client == mock_signal_client
    assert entity._entry_id == "test_entry"
    assert entity.name == "Notify"
    assert entity.unique_id == "test_entry_contact_+1234567890_notify"
    assert entity.icon == "mdi:message-text"


async def test_contact_notify_entity_send_message(mock_signal_client, sample_contact):
    """Test sending message via contact notify entity."""
    entity = SignalContactNotifyEntity(mock_signal_client, sample_contact, "test_entry")

    await entity.async_send_message(message="Hello", title="Greeting")

    mock_signal_client.send_message.assert_called_once_with(
        target="+1234567890",
        message="Greeting\n\nHello",
        base64_attachments=[],
    )


async def test_contact_notify_entity_send_message_no_title(
    mock_signal_client, sample_contact
):
    """Test sending message without title."""
    entity = SignalContactNotifyEntity(mock_signal_client, sample_contact, "test_entry")

    await entity.async_send_message(message="Hello")

    mock_signal_client.send_message.assert_called_once_with(
        target="+1234567890",
        message="Hello",
        base64_attachments=[],
    )


async def test_contact_notify_entity_send_message_error(
    mock_signal_client, sample_contact
):
    """Test error handling when sending message."""
    entity = SignalContactNotifyEntity(mock_signal_client, sample_contact, "test_entry")
    mock_signal_client.send_message.side_effect = Exception("Send failed")

    with pytest.raises(Exception, match="Send failed"):
        await entity.async_send_message(message="Hello")


def test_contact_notify_entity_device_info(mock_signal_client, sample_contact):
    """Test contact notify entity device info."""
    entity = SignalContactNotifyEntity(mock_signal_client, sample_contact, "test_entry")
    device_info = entity.device_info

    from custom_components.signal_gateway.const import DOMAIN

    assert device_info["identifiers"] == {(DOMAIN, "test_entry_contact_+1234567890")}
    assert device_info["name"] == "John Doe"
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Contact"


# Test SignalGroupNotifyEntity


def test_group_notify_entity_initialization(mock_signal_client, sample_group):
    """Test group notify entity initialization."""
    entity = SignalGroupNotifyEntity(mock_signal_client, sample_group, "test_entry")

    assert entity._group == sample_group
    assert entity._client == mock_signal_client
    assert entity._entry_id == "test_entry"
    assert entity.name == "Notify"
    assert entity.unique_id == "test_entry_group_group-id-123_notify"
    assert entity.icon == "mdi:message-text"


async def test_group_notify_entity_send_message(mock_signal_client, sample_group):
    """Test sending message via group notify entity."""
    entity = SignalGroupNotifyEntity(mock_signal_client, sample_group, "test_entry")

    await entity.async_send_message(message="Hello everyone", title="Announcement")

    mock_signal_client.send_message.assert_called_once_with(
        target="group-id-123",
        message="Announcement\n\nHello everyone",
        base64_attachments=[],
    )


async def test_group_notify_entity_send_message_no_title(
    mock_signal_client, sample_group
):
    """Test sending message without title."""
    entity = SignalGroupNotifyEntity(mock_signal_client, sample_group, "test_entry")

    await entity.async_send_message(message="Hello everyone")

    mock_signal_client.send_message.assert_called_once_with(
        target="group-id-123",
        message="Hello everyone",
        base64_attachments=[],
    )


async def test_group_notify_entity_send_message_error(mock_signal_client, sample_group):
    """Test error handling when sending message."""
    entity = SignalGroupNotifyEntity(mock_signal_client, sample_group, "test_entry")
    mock_signal_client.send_message.side_effect = Exception("Send failed")

    with pytest.raises(Exception, match="Send failed"):
        await entity.async_send_message(message="Hello")


def test_group_notify_entity_device_info(mock_signal_client, sample_group):
    """Test group notify entity device info."""
    entity = SignalGroupNotifyEntity(mock_signal_client, sample_group, "test_entry")
    device_info = entity.device_info

    from custom_components.signal_gateway.const import DOMAIN

    assert device_info["identifiers"] == {(DOMAIN, "test_entry_group_group-id-123")}
    assert device_info["name"] == "Test Group"
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Group"
