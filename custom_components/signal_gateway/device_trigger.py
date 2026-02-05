"""Device triggers for Signal Gateway integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_SIGNAL_RECEIVED
from .device_helpers import async_get_signal_device, extract_device_info

_LOGGER = logging.getLogger(__name__)

# Trigger types
TRIGGER_MESSAGE_RECEIVED = "message_received"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In([TRIGGER_MESSAGE_RECEIVED]),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for Signal Gateway devices.

    Args:
        hass: Home Assistant instance
        device_id: Device ID to get triggers for

    Returns:
        List of trigger configurations
    """
    device = await async_get_signal_device(hass, device_id)
    if not device:
        return []

    triggers = []

    # Add message_received trigger for both contacts and groups
    triggers.append(
        {
            CONF_PLATFORM: "device",
            CONF_DOMAIN: DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: TRIGGER_MESSAGE_RECEIVED,
            "metadata": {},
        }
    )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: Any,
    _trigger_info: dict,
) -> CALLBACK_TYPE:
    """Attach a trigger.

    Args:
        hass: Home Assistant instance
        config: Trigger configuration
        action: Action to execute when triggered
        trigger_info: Information about the trigger

    Returns:
        Function to detach the trigger
    """
    device_id = config[CONF_DEVICE_ID]
    trigger_type = config[CONF_TYPE]

    if trigger_type != TRIGGER_MESSAGE_RECEIVED:
        _LOGGER.warning("Unknown trigger type: %s", trigger_type)
        return lambda: None

    # Get device registry to extract device identifiers
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device:
        _LOGGER.error("Device %s not found", device_id)
        return lambda: None

    # Extract the device identifier
    device_info = extract_device_info(device)
    if not device_info:
        _LOGGER.error("Could not parse device identifier for %s", device_id)
        return lambda: None

    device_type = device_info["type"]
    device_identifier = device_info["identifier"]
    device_internal_id = device_info.get("internal_id")

    _LOGGER.debug(
        "Attaching message_received trigger for %s: %s",
        device_type,
        device_identifier,
    )

    # Create event listener that manually filters messages
    async def _handle_event(event):
        """Handle the event and filter by device."""
        envelope = event.data.get("envelope", {})

        # Extract message data and metadata
        data_message = envelope.get("dataMessage", {})
        message_body = data_message.get("message", "")
        timestamp = data_message.get("timestamp")
        attachments = data_message.get("attachments", [])
        group_info = data_message.get("groupInfo", {})

        if device_type == "contact":
            # For contacts, check the source number
            if envelope.get("source") == device_identifier and not group_info:
                _LOGGER.debug(
                    "Message received from contact %s, triggering automation",
                    device_identifier,
                )
                await action(
                    {
                        "trigger": {
                            **config,
                            "platform": "device",
                            "event": event,
                            "description": f"Message from {device.name}",
                            # Message data for easy access in automations
                            "message": message_body,
                            "sender": envelope.get("source"),
                            "timestamp": timestamp,
                            "attachments": attachments,
                            "envelope": envelope,  # Full data for advanced use
                        },
                    },
                    context=event.context,
                )
        elif device_type == "group":
            # Note: groupId in websocket is the internal_id, not the API id
            # Check if the websocket internal_id matches our device's internal_id
            websocket_internal_id = group_info.get("groupId")
            _LOGGER.debug(
                "Event received for group: websocket_internal_id=%s, device_internal_id=%s",
                websocket_internal_id,
                device_internal_id,
            )
            if (
                websocket_internal_id
                and device_internal_id
                and websocket_internal_id == device_internal_id
            ):
                # Check if this device has this internal_id in its identifiers
                _LOGGER.debug(
                    "Message received in group %s (internal_id: %s), "
                    "triggering automation",
                    device.name,
                    websocket_internal_id,
                )
                await action(
                    {
                        "trigger": {
                            **config,
                            "platform": "device",
                            "event": event,
                            "description": f"Message in {device.name}",
                            # Message data for easy access in automations
                            "message": message_body,
                            "sender": envelope.get("source"),
                            "timestamp": timestamp,
                            "attachments": attachments,
                            "group_info": group_info,
                            "envelope": envelope,  # Full data for advanced use
                        },
                    },
                    context=event.context,
                )

    return hass.bus.async_listen(EVENT_SIGNAL_RECEIVED, _handle_event)


async def async_get_trigger_capabilities(
    _hass: HomeAssistant, _config: ConfigType
) -> dict[str, vol.Schema]:
    """Get trigger capabilities.

    Args:
        hass: Home Assistant instance
        config: Trigger configuration

    Returns:
        Trigger capabilities (empty for now)
    """
    return {}
