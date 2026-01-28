"""Config flow for Signal Gateway integration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_PHONE_NUMBER,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class DuplicateServiceNameError(Exception):
    """Exception raised when a duplicate service name is detected."""


def validate_signal_gateway_input(
    user_input: dict[str, Any],
    existing_entries: list,
    exclude_entry_id: str | None = None,
) -> None:
    """Validate Signal Gateway user input.

    Args:
        user_input: The user input to validate
        existing_entries: List of existing config entries
        exclude_entry_id: Optional entry ID to exclude from duplicate check

    Raises:
        ValueError: If the API URL is invalid
        DuplicateServiceNameError: If a duplicate service name is detected
    """
    api_url = user_input.get(CONF_SIGNAL_CLI_REST_API_URL)
    if not api_url or not api_url.startswith("http"):
        raise ValueError("Invalid API URL")

    # Check for duplicate service names
    integration_name = user_input.get(CONF_NAME, DOMAIN)
    service_name = cv.slugify(integration_name)

    for entry in existing_entries:
        if exclude_entry_id and entry.entry_id == exclude_entry_id:
            continue
        existing_name = entry.data.get(CONF_NAME, DOMAIN)
        existing_service_name = cv.slugify(existing_name)
        if existing_service_name == service_name:
            raise DuplicateServiceNameError(
                f"Service name '{service_name}' is already in use"
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
                default=defaults.get(CONF_NAME, "Signal Gateway"),
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
        }
    )


class SignalGatewayConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Signal Gateway."""

    VERSION = 1
    MINOR_VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SignalGatewayOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the input
            try:
                validate_signal_gateway_input(user_input, self._async_current_entries())
            except ValueError as err:
                errors["base"] = "invalid_url"
                _LOGGER.error("Error validating input: %s", err)
            except DuplicateServiceNameError:
                errors["base"] = "duplicate_service_name"
            except Exception as err:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                _LOGGER.error("Unknown error: %s", err)
            else:
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "Signal Gateway"),
                    data=user_input,
                )

        # Build schema with defaults from user_input if available (to preserve data on errors)
        return self.async_show_form(
            step_id="user",
            data_schema=build_signal_gateway_schema(user_input),
            errors=errors,
        )


class SignalGatewayOptionsFlow(OptionsFlow):
    """Handle options flow for Signal Gateway."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the input
            try:
                validate_signal_gateway_input(
                    user_input,
                    self.hass.config_entries.async_entries(DOMAIN),
                    exclude_entry_id=self._config_entry.entry_id,
                )
            except ValueError as err:
                errors["base"] = "invalid_url"
                _LOGGER.error("Error validating input: %s", err)
            except DuplicateServiceNameError:
                errors["base"] = "duplicate_service_name"
            except Exception as err:  # pylint: disable=broad-except
                errors["base"] = "unknown"
                _LOGGER.error("Unknown error: %s", err)
            else:
                # Update the config entry with new data
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=user_input
                )
                return self.async_create_entry(title="", data={})

        # Get current configuration or user_input if validation failed
        defaults = user_input if user_input else self._config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=build_signal_gateway_schema(defaults),
            errors=errors,
        )
