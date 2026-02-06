"""Device triggers for Signal Gateway integration."""

from __future__ import annotations

import logging
from typing import Any, Callable

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, EVENT_SIGNAL_RECEIVED, EVENT_TYPING_INDICATOR
from .device_helpers import async_get_signal_device, extract_device_info, DeviceInfo

_LOGGER = logging.getLogger(__name__)

# Trigger types
TRIGGER_MESSAGE_RECEIVED = "message_received"
TRIGGER_TYPING_INDICATOR = "typing_indicator"

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(
            [TRIGGER_MESSAGE_RECEIVED, TRIGGER_TYPING_INDICATOR]
        ),
    }
)


class DeviceEventHandler:
    """Handler for device-specific events (messages and typing indicators)."""

    def __init__(
        self,
        action: Callable,
        config: ConfigType,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the device event handler.

        Args:
            action: Action to execute when triggered
            config: Trigger configuration
            device_info: DeviceInfo instance containing device details
        """
        self._action = action
        self._config = config
        self._device_info: DeviceInfo = device_info

    async def handle_typing_event(self, event: Event) -> None:
        """Handle typing indicator event for this device.

        Args:
            event: The typing indicator event
        """
        event_data = event.data

        # Check if this event is for our contact and entry
        if (
            event_data.get("source") == self._device_info.identifier
            and event_data.get("entry_id") == self._device_info.entry_id
        ):
            action_type = event_data.get("action", "")
            _LOGGER.debug(
                "Typing indicator from contact %s: %s, triggering automation",
                self._device_info.identifier,
                action_type,
            )
            await self._action(
                {
                    "trigger": {
                        **self._config,
                        "platform": "device",
                        "event": event,
                        "description": f"Typing indicator from {self._device_info.name}",
                        "source": event_data.get("source"),
                        "source_uuid": event_data.get("source_uuid"),
                        "action": action_type,
                        "timestamp": event_data.get("timestamp"),
                    },
                },
                context=event.context,
            )

    async def handle_message_event(self, event: Event) -> None:
        """Handle message received event for this device.

        Args:
            event: The message received event
        """
        envelope = event.data.get("envelope", {})

        # Extract message data and metadata
        data_message = envelope.get("dataMessage", {})
        message_body = data_message.get("message", "")
        timestamp = data_message.get("timestamp")
        attachments = data_message.get("attachments", [])
        group_info = data_message.get("groupInfo", {})

        if self._device_info.type == "contact":
            # For contacts, check the source number
            if (
                envelope.get("source") == self._device_info.identifier
                and not group_info
            ):
                _LOGGER.debug(
                    "Message received from contact %s, triggering automation",
                    self._device_info.identifier,
                )
                await self._action(
                    {
                        "trigger": {
                            **self._config,
                            "platform": "device",
                            "event": event,
                            "description": f"Message from {self._device_info.name}",
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
        elif self._device_info.type == "group":
            # Note: groupId in websocket is the internal_id, not the API id
            # Check if the websocket internal_id matches our device's internal_id
            websocket_internal_id = group_info.get("groupId")
            _LOGGER.debug(
                "Event received for group: websocket_internal_id=%s, device_internal_id=%s",
                websocket_internal_id,
                self._device_info.internal_id,
            )
            if (
                websocket_internal_id
                and self._device_info.internal_id
                and websocket_internal_id == self._device_info.internal_id
            ):
                # Check if this device has this internal_id in its identifiers
                _LOGGER.debug(
                    "Message received in group %s (internal_id: %s), "
                    "triggering automation",
                    self._device_info.name,
                    websocket_internal_id,
                )
                await self._action(
                    {
                        "trigger": {
                            **self._config,
                            "platform": "device",
                            "event": event,
                            "description": f"Message in {self._device_info.name}",
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

    # Extract device info to determine type
    device_info = extract_device_info(device)

    # Add typing_indicator trigger only for contact devices
    if device_info and device_info.type == "contact":
        triggers.append(
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: TRIGGER_TYPING_INDICATOR,
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

    if trigger_type not in (TRIGGER_MESSAGE_RECEIVED, TRIGGER_TYPING_INDICATOR):
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
    if not device_info or device.name is None:
        _LOGGER.error("Could not parse device identifier for %s", device_id)
        return lambda: None

    _LOGGER.debug(
        "Attaching %s trigger for %s: %s",
        trigger_type,
        device_info.type,
        device_info.name,
    )

    # Create device event handler instance
    handler = DeviceEventHandler(action=action, config=config, device_info=device_info)

    if trigger_type == TRIGGER_TYPING_INDICATOR:
        # Handle typing indicator trigger
        if device_info.type != "contact":
            _LOGGER.error(
                "Typing indicator trigger only supported for contacts, not %s",
                device_info.type,
            )
            return lambda: None

        return hass.bus.async_listen(
            f"{DOMAIN}_{EVENT_TYPING_INDICATOR}",
            handler.handle_typing_event,
        )

    if trigger_type == TRIGGER_MESSAGE_RECEIVED:
        # Handle message_received trigger
        return hass.bus.async_listen(
            EVENT_SIGNAL_RECEIVED, handler.handle_message_event
        )

    raise ValueError(f"Unsupported trigger type: {trigger_type}")


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
