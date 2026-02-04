"""Device discovery logic for Signal Gateway."""

import logging

import aiohttp
from homeassistant.core import HomeAssistant

from ..signal.client import SignalClient

_LOGGER = logging.getLogger(__name__)


async def discover_devices(  # pylint: disable=unused-argument
    hass: HomeAssistant,
    api_url: str,
    phone_number: str,
    session: aiohttp.ClientSession,
) -> dict[str, str]:
    """Discover available devices (contacts and groups) from Signal API.

    Args:
        hass: Home Assistant instance
        api_url: Signal CLI REST API URL
        phone_number: Phone number for the Signal account
        session: aiohttp client session

    Returns:
        Dictionary mapping device_id to display_name
        Format: {"contact_+1234567890": "John Doe", "group_abc123": "Family"}

    Raises:
        aiohttp.ClientError: If connection to API fails
        Exception: For other unexpected errors
    """
    client = SignalClient(api_url, phone_number, session)

    contacts = await client.list_contacts()
    groups = await client.list_groups()

    devices = {}

    # Add contacts
    for contact in contacts:
        device_id = f"contact_{contact.number}"
        display_name = contact.display_name
        devices[device_id] = display_name

    # Add groups
    for group in groups:
        device_id = f"group_{group.id}"
        display_name = group.name
        devices[device_id] = display_name

    _LOGGER.debug(
        "Discovered %d devices (%d contacts, %d groups)",
        len(devices),
        len(contacts),
        len(groups),
    )

    return devices
