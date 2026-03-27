"""Helper functions for device automation."""

from __future__ import annotations


def build_contact_device_identifier(entry_id: str, phone_number: str) -> str:
    """Build device identifier for a contact.

    Args:
        entry_id: Config entry ID
        phone_number: Contact phone number

    Returns:
        Device identifier string
    """
    return f"{entry_id}_contact_{phone_number}"


def build_group_device_identifier(entry_id: str, group_id: str) -> str:
    """Build device identifier for a group (API ID).

    Args:
        entry_id: Config entry ID
        group_id: Group API ID

    Returns:
        Device identifier string
    """
    return f"{entry_id}_group_{group_id}"


def build_group_internal_identifier(entry_id: str, internal_id: str) -> str:
    """Build internal device identifier for a group (websocket ID).

    Args:
        entry_id: Config entry ID
        internal_id: Group internal ID (used in websocket messages)

    Returns:
        Device identifier string
    """
    return f"{entry_id}_group-internal_{internal_id}"
