"""Device discovery logic for Signal Gateway."""

import logging

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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


async def fetch_available_devices(
    hass: HomeAssistant,
    api_url: str,
    phone_number: str,
    cached_devices: dict[str, str] | None = None,
) -> tuple[dict[str, str], str | None]:
    """Fetch available devices from Signal API with error handling.

    This is a helper function to avoid code duplication between config flow
    and options flow.

    Args:
        hass: Home Assistant instance
        api_url: Signal CLI REST API URL
        phone_number: Phone number for the Signal account
        cached_devices: Previously fetched devices (None to force fetch)

    Returns:
        Tuple of (devices_dict, error_key) where:
        - devices_dict: Dictionary mapping device_id to display_name
        - error_key: Error key for config flow errors dict, or None if successful
          Possible values: "cannot_connect", "unknown"
    """
    # Return cached devices if available
    if cached_devices:
        return cached_devices, None

    try:
        session = async_get_clientsession(hass)
        devices = await discover_devices(
            hass,
            api_url,
            phone_number,
            session,
        )
        return devices, None
    except aiohttp.ClientError as err:
        # Network/API error - show user-friendly message
        _LOGGER.error("Cannot connect to Signal API: %s", err)
        return {}, "cannot_connect"
    except Exception as err:  # pylint: disable=broad-except
        # Unexpected error (e.g. data parsing) - show generic error
        # This is a safety net, should rarely happen
        _LOGGER.exception("Unexpected error fetching devices: %s", err)
        return {}, "unknown"
