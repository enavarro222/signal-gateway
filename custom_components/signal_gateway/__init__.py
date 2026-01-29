"""The Signal Gateway integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
    EVENT_SIGNAL_RECEIVED,
)
from .signal import SignalClient
from .notify import async_unload_notify_service

_LOGGER: logging.Logger = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.NOTIFY]


def parse_recipients(recipients_str: str) -> list[str]:
    """Parse recipients from a string supporting newlines and/or commas.

    Args:
        recipients_str: String containing recipients separated by newlines and/or commas

    Returns:
        List of recipient phone numbers/IDs with whitespace stripped

    Examples:
        >>> parse_recipients("+1234567890")
        ['+1234567890']

        >>> parse_recipients("+1234567890, +9876543210")
        ['+1234567890', '+9876543210']

        >>> parse_recipients("+1234567890\\n+9876543210")
        ['+1234567890', '+9876543210']

        >>> parse_recipients("+1234567890, +9876543210\\n+5551234567")
        ['+1234567890', '+9876543210', '+5551234567']

        >>> parse_recipients("  +1234567890  ,  +9876543210  ")
        ['+1234567890', '+9876543210']

        >>> parse_recipients("")
        []

        >>> parse_recipients("  \\n  \\n  ")
        []
    """
    recipients = []
    if recipients_str:
        # Split by newlines first, then by commas, and filter out empty entries
        for line in recipients_str.splitlines():
            for recipient in line.split(","):
                recipient = recipient.strip()
                if recipient:
                    recipients.append(recipient)
    return recipients


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Signal Gateway from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    api_url = str(entry.data.get(CONF_SIGNAL_CLI_REST_API_URL, ""))
    phone_number = str(entry.data.get(CONF_PHONE_NUMBER, ""))
    websocket_enabled = entry.data.get(CONF_WEBSOCKET_ENABLED, True)

    # Create the Signal client
    session = async_get_clientsession(hass)
    client = SignalClient(api_url, phone_number, session)

    # Normalize the integration name for the service
    integration_name = entry.data.get(CONF_NAME, DOMAIN)
    service_name = cv.slugify(integration_name)

    # Check for duplicate service names across all entries
    for other_entry_id, other_data in hass.data[DOMAIN].items():
        if other_entry_id != entry.entry_id:
            other_service_name = other_data.get("service_name")
            if other_service_name == service_name:
                _LOGGER.error(
                    "Cannot setup Signal Gateway '%s': service name '%s' "
                    "is already in use by another entry",
                    integration_name,
                    service_name,
                )
                return False

    _LOGGER.debug("Singal Gateway integration setup (name: %s)", service_name)

    # Get default recipients if configured
    recipients_str = entry.data.get(CONF_RECIPIENTS, "")
    default_recipients = parse_recipients(recipients_str)

    # Store the client, service_name, and default recipients
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "service_name": service_name,
        "default_recipients": default_recipients,
    }

    # Set up WebSocket listener if enabled
    if websocket_enabled:

        async def _handle_message(data: dict) -> None:
            """Handle incoming Signal messages."""
            try:
                hass.bus.async_fire(
                    EVENT_SIGNAL_RECEIVED,
                    data,
                )
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Error processing Signal message: %s", err)

        client.set_message_handler(_handle_message)
        await client.start_listening()
        _LOGGER.info("Signal WebSocket listener started")

    # Load the notify platform for this entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register update listener for config changes
    entry.add_update_listener(async_reload_entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    service_name = data.get("service_name")
    _LOGGER.info("Unload Signal Gateway entry '%s'", service_name)

    # Stop the WebSocket listener
    client = data.get("client")
    if client:
        await client.stop_listening()
        _LOGGER.info("Signal WebSocket listener stopped")

    # Unload the notification platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Manually unload the notify service (this is not done by platform unload)
    await async_unload_notify_service(hass, entry)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
