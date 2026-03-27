"""Unit tests for Signal Gateway sensor platform (info entities)."""

import pytest

from custom_components.signal_gateway.sensor import (
    SignalContactInfoEntity,
    SignalGroupInfoEntity,
)
from custom_components.signal_gateway.signal.models import (
    ContactNickname,
    GroupPermissions,
    SignalContact,
    SignalGroup,
)


@pytest.fixture
def sample_contact_full():
    """Create a full contact with all fields."""
    return SignalContact(
        number="+1234567890",
        uuid="test-uuid",
        name="John Doe",
        given_name="John",
        profile_name="JDoe",
        username="johndoe",
    )


@pytest.fixture
def sample_contact_minimal():
    """Create a minimal contact."""
    return SignalContact(
        number="+9876543210",
        uuid="minimal-uuid",
    )


@pytest.fixture
def sample_group_full():
    """Create a full group with all fields."""
    return SignalGroup(
        id="group-id-123",
        name="Test Group",
        internal_id="internal-123",
        members=["+1234567890", "+9876543210"],
        admins=["+1234567890"],
        description="A test group",
        permissions=GroupPermissions(
            add_members="only-admins",
            edit_group="only-admins",
            send_messages="every-member",
        ),
    )


# Test SignalContactInfoEntity


def test_contact_info_entity_initialization(mock_signal_client, sample_contact_full):
    """Test contact info entity initialization."""
    entity = SignalContactInfoEntity(
        mock_signal_client, sample_contact_full, "test_entry"
    )

    assert entity._contact == sample_contact_full
    assert entity._client == mock_signal_client
    assert entity._entry_id == "test_entry"
    assert entity.name == "Info"
    assert entity.unique_id == "test_entry_contact_+1234567890_info"
    assert entity.native_value == "John Doe"
    assert entity.icon == "mdi:account-details"


def test_contact_info_entity_attributes_full(mock_signal_client, sample_contact_full):
    """Test contact info entity attributes with full data."""
    entity = SignalContactInfoEntity(
        mock_signal_client, sample_contact_full, "test_entry"
    )
    attrs = entity.extra_state_attributes

    assert attrs["number"] == "+1234567890"
    assert attrs["uuid"] == "test-uuid"
    assert attrs["type"] == "contact"
    assert attrs["name"] == "John Doe"
    assert attrs["given_name"] == "John"
    assert attrs["profile_name"] == "JDoe"
    assert attrs["username"] == "johndoe"


def test_contact_info_entity_attributes_minimal(
    mock_signal_client, sample_contact_minimal
):
    """Test contact info entity attributes with minimal data."""
    entity = SignalContactInfoEntity(
        mock_signal_client, sample_contact_minimal, "test_entry"
    )
    attrs = entity.extra_state_attributes

    assert attrs["number"] == "+9876543210"
    assert attrs["uuid"] == "minimal-uuid"
    assert attrs["type"] == "contact"
    assert "name" not in attrs
    assert "username" not in attrs


def test_contact_info_entity_with_nickname(mock_signal_client):
    """Test contact info entity with nickname."""
    contact = SignalContact(
        number="+1234567890",
        uuid="test-uuid",
        nickname=ContactNickname(given_name="Johnny", family_name="D"),
    )
    entity = SignalContactInfoEntity(mock_signal_client, contact, "test_entry")
    attrs = entity.extra_state_attributes

    assert attrs["nickname"] == "Johnny"
    assert attrs["nickname_family"] == "D"


def test_contact_info_entity_device_info(mock_signal_client, sample_contact_full):
    """Test contact info entity device info."""
    entity = SignalContactInfoEntity(
        mock_signal_client, sample_contact_full, "test_entry"
    )
    device_info = entity.device_info

    from custom_components.signal_gateway.const import DOMAIN

    assert device_info["identifiers"] == {(DOMAIN, "test_entry_contact_+1234567890")}
    assert device_info["name"] == "John Doe"
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Contact"


# Test SignalGroupInfoEntity


def test_group_info_entity_initialization(mock_signal_client, sample_group_full):
    """Test group info entity initialization."""
    entity = SignalGroupInfoEntity(mock_signal_client, sample_group_full, "test_entry")

    assert entity._group == sample_group_full
    assert entity._client == mock_signal_client
    assert entity._entry_id == "test_entry"
    assert entity.name == "Info"
    assert entity.unique_id == "test_entry_group_group-id-123_info"
    assert entity.native_value == "Test Group"
    assert entity.icon == "mdi:account-group-outline"


def test_group_info_entity_attributes(mock_signal_client, sample_group_full):
    """Test group info entity attributes."""
    entity = SignalGroupInfoEntity(mock_signal_client, sample_group_full, "test_entry")
    attrs = entity.extra_state_attributes

    assert attrs["group_id"] == "group-id-123"
    assert attrs["internal_id"] == "internal-123"
    assert attrs["type"] == "group"
    assert attrs["member_count"] == 2
    assert attrs["members"] == ["+1234567890", "+9876543210"]
    assert attrs["admins"] == ["+1234567890"]
    assert attrs["description"] == "A test group"
    assert attrs["permissions"]["add_members"] == "only-admins"


def test_group_info_entity_attributes_minimal(mock_signal_client):
    """Test group info entity attributes with minimal data."""
    group = SignalGroup(
        id="minimal-group",
        name="Minimal",
        internal_id="internal-minimal",
    )
    entity = SignalGroupInfoEntity(mock_signal_client, group, "test_entry")
    attrs = entity.extra_state_attributes

    assert attrs["group_id"] == "minimal-group"
    assert attrs["type"] == "group"
    assert attrs["member_count"] == 0
    assert "description" not in attrs
    assert "permissions" not in attrs


def test_group_info_entity_device_info(mock_signal_client, sample_group_full):
    """Test group info entity device info."""
    entity = SignalGroupInfoEntity(mock_signal_client, sample_group_full, "test_entry")
    device_info = entity.device_info

    from custom_components.signal_gateway.const import DOMAIN

    # Groups have two identifiers: API id and internal_id (for websocket matching)
    assert device_info["identifiers"] == {
        (DOMAIN, "test_entry_group_group-id-123"),
        (DOMAIN, "test_entry_group-internal_internal-123"),
    }
    assert device_info["name"] == "Test Group"
    assert device_info["manufacturer"] == "Signal Messenger"
    assert device_info["model"] == "Group"
