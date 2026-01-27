"""Notification service for Signal Gateway."""

from __future__ import annotations

import logging
from typing import Any, Optional, Union

import voluptuous as vol

from homeassistant.components.notify import (
    BaseNotificationService,
    DOMAIN as NOTIFY_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_set_service_schema

from .const import DOMAIN
from .signal import SignalClient

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_MESSAGE = "send_message"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> bool:
    """Set up Signal Gateway notify from a config entry."""
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Signal Gateway client not found for entry %s", entry.entry_id)
        return False

    client = hass.data[DOMAIN][entry.entry_id].get("client")
    if not client:
        _LOGGER.error("Signal Gateway client not initialized")
        return False

    # Create the notification service
    service = SignalGatewayNotificationService(hass, client)

    # Register the Home Assistant service
    async def handle_send_message(call):
        """Handle send message service call."""
        await service.async_send_message(
            message=call.data.get("message"),
            title=call.data.get("title"),
            target=call.data.get("target"),
            attachments=call.data.get("attachments"),
        )

    # Get the service name from the config entry
    service_name = hass.data[DOMAIN][entry.entry_id]["service_name"]

    _LOGGER.debug(
        "Registering Signal Gateway notify service '%s' for entry %s",
        service_name,
        entry.entry_id,
    )
    hass.services.async_register(
        DOMAIN,
        service_name,
        handle_send_message,
        schema=vol.Schema(
            {
                vol.Required("message"): cv.string,
                vol.Optional("title"): cv.string,
                vol.Required("target"): vol.Any(cv.string, [cv.string]),
                vol.Optional("attachments"): [cv.string],
            }
        ),
    )

    # Set service schema for GUI
    async_set_service_schema(
        hass,
        DOMAIN,
        service_name,
        {
            "name": "Send message",
            "description": "Send a Signal message to one or more recipients",
            "fields": {
                "message": {
                    "name": "Message",
                    "description": "The message content to send",
                    "required": True,
                    "example": "Hello from Home Assistant!",
                    "selector": {"text": {"multiline": True}},
                },
                "title": {
                    "name": "Title",
                    "description": "Optional title that will be prepended to the message",
                    "required": False,
                    "example": "Alert",
                    "selector": {"text": {}},
                },
                "target": {
                    "name": "Target",
                    "description": "Phone number (with country code) or group ID. Can be a single value or a list",
                    "required": True,
                    "example": "+1234567890",
                    "selector": {"text": {}},
                },
                "attachments": {
                    "name": "Attachments",
                    "description": "List of file paths or URLs to attach to the message",
                    "required": False,
                    "example": ["/config/www/camera_snapshot.jpg"],
                    "selector": {"object": {}},
                },
            },
        },
    )
    return True


async def async_unload_notify_service(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Signal Gateway notify entry."""
    # Note: this could be a "async_unload_entry" called when "async_forward_entry_setups"
    # is called in __init__.py
    # however this do not work with the notify platform so we do it manually here
    _LOGGER.info("Unloading Signal Gateway notify entry %s", entry.entry_id)
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    service_name = data.get("service_name")

    if service_name:
        _LOGGER.debug(
            "Unregistering Signal Gateway notify service '%s' for entry %s",
            service_name,
            entry.entry_id,
        )
        hass.services.async_remove(DOMAIN, service_name)

    return True


class SignalGatewayNotificationService(BaseNotificationService):
    """Signal Gateway notification service for Home Assistant."""

    def __init__(self, hass: HomeAssistant, client: SignalClient) -> None:
        """Initialize the notification service."""
        self.hass = hass
        self._client: SignalClient = client

    def send_message(self, message, **kwargs):
        raise NotImplementedError("Use async_send_message instead")

    async def async_send_message(
        self,
        message: Optional[str] = None,
        title: Optional[str] = None,
        target: Optional[Union[str, list[Any]]] = None,
        attachments: Optional[list[Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Send a notification via Signal.

        Args:
            message: The message to send
            title: Optional title (prepended to message)
            target: Phone number or group ID
            attachments: List of attachment URLs
        """
        if not message:
            _LOGGER.error("Message is required")
            return

        if not target:
            _LOGGER.error("Target (phone number or group ID) is required")
            return

        # Ensure target is a list
        if isinstance(target, str):
            targets = [target]
        else:
            targets = target

        # Prepend title if provided
        full_message = message
        if title:
            full_message = f"{title}\n{message}"

        # Send to each recipient
        for recipient in targets:
            try:
                # Home Assistant phone numbers may not include the '+' prefix
                if not recipient.startswith("+"):
                    recipient = f"+{recipient}"
                result = await self._client.send_message(
                    target=recipient,
                    message=full_message,
                    attachments=attachments,
                )
                _LOGGER.info("Notification sent successfully to %s", recipient)
                _LOGGER.debug("Send result: %s", result)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Failed to send notification to %s: %s", recipient, err)
