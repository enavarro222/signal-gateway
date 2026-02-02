"""Tests for Signal data models."""

import pytest
from custom_components.signal_gateway.signal.models import (
    SignalGroup,
    SignalContact,
    ContactProfile,
    ContactNickname,
    GroupPermissions,
)


# ContactProfile tests


def test_contact_profile_from_api_full_data():
    """Test creating ContactProfile from full API data (matches swagger spec)."""
    data = {
        "about": "Available 24/7",
        "given_name": "John",
        "lastname": "Doe",
        "has_avatar": True,
        "last_updated_timestamp": 1234567890,
    }
    profile = ContactProfile.from_api(data)

    assert profile.about == "Available 24/7"
    assert profile.given_name == "John"
    assert profile.lastname == "Doe"
    assert profile.has_avatar is True
    assert profile.last_updated_timestamp == 1234567890


def test_contact_profile_from_api_empty_data():
    """Test creating ContactProfile from None."""
    profile = ContactProfile.from_api(None)

    assert profile.about == ""
    assert profile.given_name == ""
    assert profile.has_avatar is False


def test_contact_profile_from_api_partial_data():
    """Test creating ContactProfile from partial data."""
    data = {"about": "Hello", "has_avatar": True}
    profile = ContactProfile.from_api(data)

    assert profile.about == "Hello"
    assert profile.has_avatar is True
    assert profile.given_name == ""
    assert profile.lastname == ""


# ContactNickname tests


def test_contact_nickname_from_api_full_data():
    """Test creating ContactNickname from full API data (matches swagger spec)."""
    data = {
        "name": "Johnny",
        "given_name": "John",
        "family_name": "Doe",
    }
    nickname = ContactNickname.from_api(data)

    assert nickname.name == "Johnny"
    assert nickname.given_name == "John"
    assert nickname.family_name == "Doe"


def test_contact_nickname_from_api_none():
    """Test creating ContactNickname from None."""
    nickname = ContactNickname.from_api(None)

    assert nickname.name == ""
    assert nickname.given_name == ""
    assert nickname.family_name == ""


# SignalContact tests


def test_signal_contact_from_api_full_data():
    """Test creating SignalContact from full API data (matches swagger ListContactsResponse)."""
    data = {
        "number": "+1234567890",
        "uuid": "uuid-1234",
        "name": "John Doe",
        "profile_name": "John",
        "given_name": "Johnny",
        "username": "johndoe.123",
        "profile": {
            "about": "Available",
            "given_name": "John",
            "has_avatar": True,
        },
        "nickname": {
            "name": "Johnny Boy",
            "given_name": "Johnny",
        },
        "note": "Friend from work",
        "color": "#FF5733",
        "message_expiration": "3600",
        "blocked": False,
    }
    contact = SignalContact.from_api(data)

    assert contact.number == "+1234567890"
    assert contact.uuid == "uuid-1234"
    assert contact.name == "John Doe"
    assert contact.profile_name == "John"
    assert contact.given_name == "Johnny"
    assert contact.username == "johndoe.123"
    assert contact.profile.about == "Available"
    assert contact.nickname.name == "Johnny Boy"
    assert contact.note == "Friend from work"
    assert contact.color == "#FF5733"
    assert contact.message_expiration == "3600"
    assert contact.blocked is False


def test_signal_contact_from_api_minimal_data():
    """Test creating SignalContact from minimal required data."""
    data = {
        "number": "+9999999999",
        "uuid": "uuid-minimal",
    }
    contact = SignalContact.from_api(data)

    assert contact.number == "+9999999999"
    assert contact.uuid == "uuid-minimal"
    assert contact.name == ""
    assert contact.profile.about == ""
    assert contact.nickname.name == ""


def test_signal_contact_display_name_priority():
    """Test display_name property uses correct priority (per implementation): name > profile_name > given_name > username > number."""
    # Priority 1: name
    contact1 = SignalContact.from_api(
        {
            "number": "+1111",
            "uuid": "uuid-1",
            "name": "Full Name",
            "profile_name": "Profile",
            "given_name": "Given",
        }
    )
    assert contact1.display_name == "Full Name"

    # Priority 2: profile_name (no name)
    contact2 = SignalContact.from_api(
        {
            "number": "+2222",
            "uuid": "uuid-2",
            "profile_name": "Profile",
            "given_name": "Given",
        }
    )
    assert contact2.display_name == "Profile"

    # Priority 3: given_name (no name, no profile_name)
    contact3 = SignalContact.from_api(
        {
            "number": "+3333",
            "uuid": "uuid-3",
            "given_name": "Given",
        }
    )
    assert contact3.display_name == "Given"

    # Priority 4: username (no name, no profile_name, no given_name)
    contact4 = SignalContact.from_api(
        {
            "number": "+4444",
            "uuid": "uuid-4",
            "username": "user123",
        }
    )
    assert contact4.display_name == "user123"

    # Priority 5: number (nothing else)
    contact5 = SignalContact.from_api(
        {
            "number": "+5555",
            "uuid": "uuid-5",
        }
    )
    assert contact5.display_name == "+5555"


# GroupPermissions tests


def test_group_permissions_from_api_full_data():
    """Test creating GroupPermissions from full API data (matches swagger spec)."""
    data = {
        "add_members": "only-admins",
        "edit_group": "only-admins",
        "send_messages": "every-member",
    }
    perms = GroupPermissions.from_api(data)

    assert perms.add_members == "only-admins"
    assert perms.edit_group == "only-admins"
    assert perms.send_messages == "every-member"


def test_group_permissions_from_api_defaults():
    """Test GroupPermissions defaults when no data provided (per implementation)."""
    perms = GroupPermissions.from_api(None)

    # Check actual defaults from the model implementation
    assert perms.add_members == "every-member"
    assert perms.edit_group == "only-admins"
    assert perms.send_messages == "every-member"


def test_group_permissions_to_api():
    """Test converting GroupPermissions back to API dict."""
    perms = GroupPermissions(
        add_members="only-admins",
        edit_group="only-admins",
        send_messages="only-admins",
    )
    api_dict = perms.to_api()

    assert api_dict == {
        "add_members": "only-admins",
        "edit_group": "only-admins",
        "send_messages": "only-admins",
    }


# SignalGroup tests


def test_signal_group_from_api_full_data():
    """Test creating SignalGroup from full API data (matches swagger GroupEntry)."""
    data = {
        "id": "group.abc123",
        "name": "Family Group",
        "internal_id": "internal123",
        "members": ["+1111", "+2222", "+3333"],
        "admins": ["+1111", "+2222"],
        "description": "Our family chat",
        "invite_link": "https://signal.group/...",
        "blocked": False,
        "pending_invites": ["+4444"],
        "pending_requests": ["+5555"],
    }
    group = SignalGroup.from_api(data)

    assert group.id == "group.abc123"
    assert group.name == "Family Group"
    assert group.internal_id == "internal123"
    assert group.members == ["+1111", "+2222", "+3333"]
    assert group.admins == ["+1111", "+2222"]
    assert group.description == "Our family chat"
    assert group.invite_link == "https://signal.group/..."
    assert group.blocked is False
    assert group.pending_invites == ["+4444"]
    assert group.pending_requests == ["+5555"]


def test_signal_group_from_api_minimal_data():
    """Test creating SignalGroup from minimal required data."""
    data = {
        "id": "group.minimal",
        "name": "Simple Group",
        "internal_id": "internal456",
        "members": ["+1111"],
        "admins": ["+1111"],
    }
    group = SignalGroup.from_api(data)

    assert group.id == "group.minimal"
    assert group.name == "Simple Group"
    assert group.members == ["+1111"]
    assert group.description == ""
    assert group.invite_link is None


def test_signal_group_member_count_property():
    """Test member_count computed property."""
    group = SignalGroup.from_api(
        {
            "id": "group.test",
            "name": "Test",
            "internal_id": "internal",
            "members": ["+1111", "+2222", "+3333", "+4444"],
            "admins": ["+1111"],
        }
    )
    assert group.member_count == 4


def test_signal_group_is_admin_only_property():
    """Test is_admin_only computed property based on permissions."""
    # Admin-only group
    group_admin_only = SignalGroup.from_api(
        {
            "id": "group.admin",
            "name": "Admin Only",
            "internal_id": "internal",
            "members": ["+1111"],
            "admins": ["+1111"],
            "permissions": {
                "add_members": "only-admins",
                "edit_group": "only-admins",
                "send_messages": "only-admins",
            },
        }
    )
    assert group_admin_only.is_admin_only is True

    # Open group
    group_open = SignalGroup.from_api(
        {
            "id": "group.open",
            "name": "Open",
            "internal_id": "internal",
            "members": ["+1111"],
            "admins": ["+1111"],
            "permissions": {
                "add_members": "every-member",
                "edit_group": "every-member",
                "send_messages": "every-member",
            },
        }
    )
    assert group_open.is_admin_only is False

    # Mixed permissions (not fully admin-only)
    group_mixed = SignalGroup.from_api(
        {
            "id": "group.mixed",
            "name": "Mixed",
            "internal_id": "internal",
            "members": ["+1111"],
            "admins": ["+1111"],
            "permissions": {
                "add_members": "only-admins",
                "edit_group": "every-member",
                "send_messages": "every-member",
            },
        }
    )
    assert group_mixed.is_admin_only is False
