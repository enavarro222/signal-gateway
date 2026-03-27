"""Data models for Signal Gateway."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContactProfile:
    """Contact's Signal profile information."""

    about: str = ""
    given_name: str = ""
    lastname: str = ""
    has_avatar: bool = False
    last_updated_timestamp: int = 0

    @classmethod
    def from_api(cls, data: dict | None) -> ContactProfile:
        """Create from API response.

        Args:
            data: Profile data from API

        Returns:
            ContactProfile instance
        """
        if not data:
            return cls()
        return cls(
            about=data.get("about", ""),
            given_name=data.get("given_name", ""),
            lastname=data.get("lastname", ""),
            has_avatar=data.get("has_avatar", False),
            last_updated_timestamp=data.get("last_updated_timestamp", 0),
        )


@dataclass
class ContactNickname:
    """Contact's local nickname."""

    name: str = ""
    given_name: str = ""
    family_name: str = ""

    @classmethod
    def from_api(cls, data: dict | None) -> ContactNickname:
        """Create from API response.

        Args:
            data: Nickname data from API

        Returns:
            ContactNickname instance
        """
        if not data:
            return cls()
        return cls(
            name=data.get("name", ""),
            given_name=data.get("given_name", ""),
            family_name=data.get("family_name", ""),
        )


@dataclass
class SignalContact:  # pylint: disable=too-many-instance-attributes
    """Represents a Signal contact."""

    number: str
    uuid: str
    name: str = ""
    given_name: str = ""
    profile_name: str = ""
    username: Optional[str] = None
    nickname: Optional[ContactNickname] = None
    profile: Optional[ContactProfile] = None
    note: str = ""
    color: str = ""
    message_expiration: str = "0"
    blocked: bool = False

    @classmethod
    def from_api(cls, data: dict) -> SignalContact:
        """Create from API response.

        Args:
            data: Contact data from API

        Returns:
            SignalContact instance
        """
        return cls(
            number=data.get("number", ""),
            uuid=data.get("uuid", ""),
            name=data.get("name", ""),
            given_name=data.get("given_name", ""),
            profile_name=data.get("profile_name", ""),
            username=data.get("username"),
            nickname=ContactNickname.from_api(data.get("nickname")),
            profile=ContactProfile.from_api(data.get("profile")),
            note=data.get("note", ""),
            color=data.get("color", ""),
            message_expiration=data.get("message_expiration", "0"),
            blocked=data.get("blocked", False),
        )

    @property
    def display_name(self) -> str:
        """Get the best display name for this contact.

        Returns:
            Display name in order of preference: name, profile_name, given_name, username, number
        """
        return (
            self.name
            or self.profile_name
            or self.given_name
            or self.username
            or self.number
        )


@dataclass
class GroupPermissions:
    """Signal group permissions."""

    add_members: str = "every-member"  # "only-admins" | "every-member"
    edit_group: str = "only-admins"  # "only-admins" | "every-member"
    send_messages: str = "every-member"  # "only-admins" | "every-member"

    @classmethod
    def from_api(cls, data: dict | None) -> GroupPermissions:
        """Create from API response.

        Args:
            data: Permissions data from API

        Returns:
            GroupPermissions instance
        """
        if not data:
            return cls()
        return cls(
            add_members=data.get("add_members", "every-member"),
            edit_group=data.get("edit_group", "only-admins"),
            send_messages=data.get("send_messages", "every-member"),
        )

    def to_api(self) -> dict:
        """Convert to API format.

        Returns:
            Dict suitable for API requests
        """
        return {
            "add_members": self.add_members,
            "edit_group": self.edit_group,
            "send_messages": self.send_messages,
        }


@dataclass
class SignalGroup:  # pylint: disable=too-many-instance-attributes
    """Represents a Signal group."""

    id: str
    name: str
    internal_id: str
    members: list[str] = field(default_factory=list)
    admins: list[str] = field(default_factory=list)
    description: str = ""
    invite_link: Optional[str] = None
    blocked: bool = False
    pending_invites: list[str] = field(default_factory=list)
    pending_requests: list[str] = field(default_factory=list)
    permissions: Optional[GroupPermissions] = None

    @classmethod
    def from_api(cls, data: dict) -> SignalGroup:
        """Create from API response.

        Args:
            data: Group data from API

        Returns:
            SignalGroup instance
        """
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            internal_id=data.get("internal_id", ""),
            members=data.get("members", []),
            admins=data.get("admins", []),
            description=data.get("description", ""),
            invite_link=data.get("invite_link"),
            blocked=data.get("blocked", False),
            pending_invites=data.get("pending_invites", []),
            pending_requests=data.get("pending_requests", []),
            permissions=GroupPermissions.from_api(data.get("permissions")),
        )

    @property
    def member_count(self) -> int:
        """Get the number of members in the group.

        Returns:
            Number of members
        """
        return len(self.members)

    @property
    def is_admin_only(self) -> bool:
        """Check if only admins can send messages.

        Returns:
            True if only admins can send messages
        """
        return (
            self.permissions is not None
            and self.permissions.send_messages == "only-admins"
        )
