"""Unit tests for Signal Gateway binary_sensor platform (is_writing entities)."""

import pytest

from custom_components.signal_gateway.binary_sensor import (
    SignalContactIsWritingEntity,
    SignalGroupIsWritingEntity,
)


# Test SignalContactIsWritingEntity


def test_contact_is_writing_entity_initialization(mock_signal_client, sample_contact):
    """Test contact is_writing entity initialization."""
    entity = SignalContactIsWritingEntity(
        mock_signal_client, sample_contact, "test_entry"
    )

    assert entity._contact == sample_contact
    assert entity._client == mock_signal_client
    assert entity._entry_id == "test_entry"
    assert entity.name == "Is Writing"
    assert entity.unique_id == "test_entry_contact_+1234567890_is_writing"
    assert entity.is_on is False  # Default state
    assert entity.icon == "mdi:pencil"


def test_contact_is_writing_entity_device_info(mock_signal_client, sample_contact):
    """Test contact is_writing entity device info."""
    entity = SignalContactIsWritingEntity(
        mock_signal_client, sample_contact, "test_entry"
    )
    device_info = entity.device_info

    from custom_components.signal_gateway.const import DOMAIN

    assert device_info["identifiers"] == {(DOMAIN, "test_entry_contact_+1234567890")}
    assert device_info["name"] == "John Doe"
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Contact"


# Test SignalGroupIsWritingEntity


def test_group_is_writing_entity_initialization(mock_signal_client, sample_group):
    """Test group is_writing entity initialization."""
    entity = SignalGroupIsWritingEntity(mock_signal_client, sample_group, "test_entry")

    assert entity._group == sample_group
    assert entity._client == mock_signal_client
    assert entity._entry_id == "test_entry"
    assert entity.name == "Is Writing"
    assert entity.unique_id == "test_entry_group_group-id-123_is_writing"
    assert entity.is_on is False  # Default state
    assert entity.icon == "mdi:pencil"


def test_group_is_writing_entity_device_info(mock_signal_client, sample_group):
    """Test group is_writing entity device info."""
    entity = SignalGroupIsWritingEntity(mock_signal_client, sample_group, "test_entry")
    device_info = entity.device_info

    from custom_components.signal_gateway.const import DOMAIN

    assert device_info["identifiers"] == {(DOMAIN, "test_entry_group_group-id-123")}
    assert device_info["name"] == "Test Group"
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Group"
