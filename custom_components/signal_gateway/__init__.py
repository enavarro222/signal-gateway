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
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
    EVENT_SIGNAL_RECEIVED,
)
from .signal import SignalClient, SignalWebSocketListener
from .notify import async_unload_notify_service

_LOGGER: logging.Logger = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.NOTIFY]


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

    _LOGGER.debug("Singal Gateway integration setup (name: %s)", service_name)

    # Store the client, and the service_name
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "service_name": service_name,
        "listener": None,
    }

    # Set up WebSocket listener if enabled
    if websocket_enabled:
        listener = SignalWebSocketListener(api_url, phone_number)

        async def _handle_message(data: dict) -> None:
            """Handle incoming Signal messages."""
            try:
                hass.bus.async_fire(
                    EVENT_SIGNAL_RECEIVED,
                    data,
                )
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Error processing Signal message: %s", err)

        listener.set_message_handler(_handle_message)
        await listener.connect()
        hass.data[DOMAIN][entry.entry_id]["listener"] = listener
        _LOGGER.info("Signal WebSocket listener started")

    # Load the notify platform for this entry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    service_name = data.get("service_name")
    _LOGGER.info("Unload Signal Gateway entry '%s'", service_name)

    # Stop the WebSocket listener
    listener = data.get("listener")
    if listener:
        await listener.disconnect()
        _LOGGER.info("Signal WebSocket listener stopped")

    # Unload the notification platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Manually unload the notify service (this is not done by platform unload)
    await async_unload_notify_service(hass, entry)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
