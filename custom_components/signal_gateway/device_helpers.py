"""Helper functions for device automation."""

from __future__ import annotations

import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

# Regex pattern to parse device identifiers
# Format: {entry_id}_{contact|group}_{identifier}
DEVICE_IDENTIFIER_PATTERN = re.compile(r"^(.+)_(contact|group)_(.+)$")
GROUP_INTERNAL_ID_PATTERN = re.compile(r"^.+_group-internal_(.+)$")


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


async def async_get_signal_device(
    hass: HomeAssistant, device_id: str
) -> dr.DeviceEntry | None:
    """Get a Signal Gateway device if it exists.

    Args:
        hass: Home Assistant instance
        device_id: Device ID to retrieve

    Returns:
        Device entry if it's a Signal Gateway device, None otherwise
    """
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device:
        return None

    # Check if this is a Signal Gateway device
    if not any(identifier[0] == DOMAIN for identifier in device.identifiers):
        return None

    return device


def extract_device_info(device: dr.DeviceEntry) -> dict[str, str]:
    """Extract Signal Gateway device information from device registry entry.

    Args:
        device: Device registry entry

    Returns:
        Dict with entry_id, type, and identifier or None if not a valid Signal device
    """
    device_info = {}
    for identifier in device.identifiers:
        if identifier[0] != DOMAIN:
            continue
        # Parse identifier using regex
        # Expected format: 'entry_id_contact_+33607228160' or 'entry_id_group_groupid123'
        # Internal identifiers like 'entry_id_group_internal_xxx' won't match the pattern
        match = DEVICE_IDENTIFIER_PATTERN.match(identifier[1])
        if match:
            device_info["entry_id"] = match.group(1)
            device_info["type"] = match.group(2)  # 'contact' or 'group'
            device_info["identifier"] = match.group(3)  # phone number or group
        else:
            match_internal = GROUP_INTERNAL_ID_PATTERN.match(identifier[1])
            if match_internal:
                device_info["internal_id"] = match_internal.group(1)
    return device_info
