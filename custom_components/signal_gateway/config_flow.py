"""Config flow for Signal Gateway integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from .const import (
    CONF_PHONE_NUMBER,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SignalGatewayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Signal Gateway."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the input
            try:
                await self._validate_input(user_input)
            except ValueError as err:
                errors["base"] = "invalid_url"
                _LOGGER.error("Error validating input: %s", err)
            except Exception as err:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                _LOGGER.error("Unknown error: %s", err)
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "Signal Gateway"),
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="Signal Gateway"): str,
                vol.Required(CONF_SIGNAL_CLI_REST_API_URL): str,
                vol.Required(CONF_PHONE_NUMBER): str,
                vol.Optional(CONF_WEBSOCKET_ENABLED, default=True): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def _validate_input(self, user_input: dict[str, Any]) -> None:
        """Validate the user input."""
        api_url = user_input.get(CONF_SIGNAL_CLI_REST_API_URL)
        if not api_url or not api_url.startswith("http"):
            raise ValueError("Invalid API URL")
