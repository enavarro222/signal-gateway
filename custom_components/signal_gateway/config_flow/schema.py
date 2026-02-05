"""Schema definitions for Signal Gateway configuration."""

from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

from ..const import (
    CONF_APPROVED_DEVICES,
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
)


def build_signal_gateway_schema(
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Build the schema for Signal Gateway configuration.

    Args:
        defaults: Optional dictionary with default values for the fields

    Returns:
        The voluptuous schema for the configuration form
    """
    if defaults is None:
        defaults = {}

    return vol.Schema(
        {
            vol.Optional(
                CONF_NAME,
                default=defaults.get(CONF_NAME, "Signal"),
            ): str,
            vol.Required(
                CONF_SIGNAL_CLI_REST_API_URL,
                default=defaults.get(CONF_SIGNAL_CLI_REST_API_URL, vol.UNDEFINED),
            ): str,
            vol.Required(
                CONF_PHONE_NUMBER,
                default=defaults.get(CONF_PHONE_NUMBER, vol.UNDEFINED),
            ): str,
            vol.Optional(
                CONF_WEBSOCKET_ENABLED,
                default=defaults.get(CONF_WEBSOCKET_ENABLED, True),
            ): bool,
            vol.Optional(
                CONF_RECIPIENTS,
                default=defaults.get(CONF_RECIPIENTS, ""),
            ): str,
        }
    )


def build_device_selection_schema(
    available_devices: dict[str, str],
    default_selected: list[str] | None = None,
) -> vol.Schema:
    """Build the schema for device selection.

    Args:
        available_devices: Dictionary mapping device_id to display_name
        default_selected: List of device IDs to select by default

    Returns:
        The voluptuous schema for device selection form
    """
    if default_selected is None:
        default_selected = []

    return vol.Schema(
        {
            vol.Optional(
                CONF_APPROVED_DEVICES, default=default_selected
            ): cv.multi_select(available_devices),
        }
    )
