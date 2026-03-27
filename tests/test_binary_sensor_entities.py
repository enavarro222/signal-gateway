"""Unit tests for Signal Gateway binary_sensor platform (is_writing entities)."""

import pytest
from unittest.mock import MagicMock

from custom_components.signal_gateway.binary_sensor import (
    SignalContactIsWritingEntity,
    SignalGroupIsWritingEntity,
)
from custom_components.signal_gateway.coordinator import (
    SignalContactCoordinator,
    SignalGroupCoordinator,
)
from custom_components.signal_gateway.const import DOMAIN


# Test SignalContactIsWritingEntity


def test_contact_is_writing_entity_initialization(mock_contact_coordinator, sample_contact):
    """Test contact is_writing entity initialization."""
    entity = SignalContactIsWritingEntity(mock_contact_coordinator)

    assert entity.contact == sample_contact
    assert entity.coordinator.entry_id == "test_entry_id"
    assert entity.name == "Is Writing"
    assert entity.unique_id == f"test_entry_id_contact_{sample_contact.uuid}_is_writing"
    assert entity.is_on is False
    assert entity.icon == "mdi:pencil"


def test_contact_is_writing_entity_device_info(mock_contact_coordinator, sample_contact):
    """Test contact is_writing entity device info delegates to coordinator."""
    entity = SignalContactIsWritingEntity(mock_contact_coordinator)
    device_info = entity.device_info

    assert (DOMAIN, f"test_entry_id_contact_{sample_contact.number}") in device_info["identifiers"]
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Contact"


# Test SignalGroupIsWritingEntity


def test_group_is_writing_entity_initialization(mock_group_coordinator, sample_group):
    """Test group is_writing entity initialization."""
    entity = SignalGroupIsWritingEntity(mock_group_coordinator)

    assert entity.group == sample_group
    assert entity.coordinator.entry_id == "test_entry_id"
    assert entity.name == "Is Writing"
    assert entity.unique_id == f"test_entry_id_group_{sample_group.id}_is_writing"
    assert entity.is_on is False
    assert entity.icon == "mdi:pencil"


def test_group_is_writing_entity_device_info(mock_group_coordinator, sample_group):
    """Test group is_writing entity device info delegates to coordinator."""
    entity = SignalGroupIsWritingEntity(mock_group_coordinator)
    device_info = entity.device_info

    assert (DOMAIN, f"test_entry_id_group_{sample_group.id}") in device_info["identifiers"]
    assert (DOMAIN, f"test_entry_id_group-internal_{sample_group.internal_id}") in device_info["identifiers"]
    assert device_info["name"] == sample_group.name
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Group"
