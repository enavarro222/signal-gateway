"""Schema definitions for Signal Gateway configuration."""

from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_NAME

from ..const import (
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
