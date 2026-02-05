"""Device actions for Signal Gateway integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_TYPE,
    ATTR_ENTITY_ID,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType, TemplateVarsType

from .const import DOMAIN
from .device_helpers import async_get_signal_device, extract_device_info

_LOGGER = logging.getLogger(__name__)

# Action types
ACTION_SEND_MESSAGE = "send_message"

# Action schema
ACTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TYPE): vol.In([ACTION_SEND_MESSAGE]),
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_DOMAIN): DOMAIN,
        vol.Required("message"): cv.template,
    }
)


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device actions for Signal Gateway devices.

    Args:
        hass: Home Assistant instance
        device_id: Device ID to get actions for

    Returns:
        List of action configurations
    """
    device = await async_get_signal_device(hass, device_id)
    if not device:
        return []

    actions = []

    # Add send_message action for both contacts and groups
    actions.append(
        {
            "domain": DOMAIN,
            CONF_DEVICE_ID: device_id,
            CONF_TYPE: ACTION_SEND_MESSAGE,
            "metadata": {},
        }
    )

    return actions


async def async_call_action_from_config(
    hass: HomeAssistant,
    config: ConfigType,
    variables: TemplateVarsType,
    context: Context | None,
) -> None:
    """Execute a device action.

    Args:
        hass: Home Assistant instance
        config: Action configuration
        variables: Template variables
        context: Context for the action
    """
    if config[CONF_TYPE] != ACTION_SEND_MESSAGE:
        _LOGGER.warning("Unknown action type: %s", config[CONF_TYPE])
        return

    device_id = config[CONF_DEVICE_ID]
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)

    if not device:
        _LOGGER.error("Device %s not found", device_id)
        return

    # Extract device identifier from identifiers
    device_info = extract_device_info(device)
    if not device_info:
        _LOGGER.error("Could not parse device identifier for %s", device_id)
        return

    # Render message template
    message_template = config["message"]
    message_template.hass = hass
    message = message_template.async_render(variables, parse_result=False)

    _LOGGER.debug(
        "Sending message to %s %s: %s",
        device_info["type"],
        device_info["identifier"],
        message,
    )

    # Find notify entity for this device
    entity_registry = er.async_get(hass)
    notify_entity_id = None

    # Get only entities for this device (much more efficient than iterating all entities)
    for entity in entity_registry.entities.get_entries_for_device_id(device_id):
        if entity.platform == DOMAIN and entity.domain == "notify":
            notify_entity_id = entity.entity_id
            break

    if not notify_entity_id:
        _LOGGER.error("Could not find notify entity for device %s", device_id)
        return

    # Call notify service
    await hass.services.async_call(
        "notify",
        "send_message",
        {
            ATTR_ENTITY_ID: notify_entity_id,
            "message": message,
        },
        blocking=True,
        context=context,
    )

    _LOGGER.debug("Message sent successfully to %s", device.name)


async def async_get_action_capabilities(
    _hass: HomeAssistant, config: ConfigType
) -> dict[str, vol.Schema]:
    """Get action capabilities.

    Args:
        hass: Home Assistant instance
        config: Action configuration

    Returns:
        Action capabilities with extra fields schema
    """
    if config[CONF_TYPE] == ACTION_SEND_MESSAGE:
        return {
            "extra_fields": vol.Schema(
                {
                    vol.Required("message"): str,
                }
            )
        }

    return {}
