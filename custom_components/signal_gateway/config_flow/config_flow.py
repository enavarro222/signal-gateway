"""Config flow for Signal Gateway integration."""

# pylint: disable=duplicate-code
# ConfigFlow and OptionsFlow share similar structure by design (async_step_discovery).
# They inherit from different base classes and have different responsibilities,
# making abstraction impractical. This duplication is intentional and acceptable.

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from ..const import (
    CONF_APPROVED_DEVICES,
    CONF_PHONE_NUMBER,
    CONF_SIGNAL_CLI_REST_API_URL,
    DOMAIN,
)
from .discovery import fetch_available_devices
from .schema import build_signal_gateway_schema, build_device_selection_schema
from .validation import DuplicateServiceNameError, validate_signal_gateway_input
from .options_flow import SignalGatewayOptionsFlow

_LOGGER = logging.getLogger(__name__)


class SignalGatewayConfigFlow(
    ConfigFlow, domain=DOMAIN
):  # pylint: disable=abstract-method
    """Handle a config flow for Signal Gateway."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._user_input: dict[str, Any] = {}
        self._available_devices: dict[str, Any] = {}

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
                # Store user input and proceed to discovery step
                self._user_input = user_input
                return await self.async_step_discovery()

        # Build schema with defaults from user_input if available (to preserve data on errors)
        return self.async_show_form(
            step_id="user",
            data_schema=build_signal_gateway_schema(user_input),
            errors=errors,
        )

    async def async_step_discovery(
        self, discovery_info: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device discovery step."""
        errors: dict[str, str] = {}
        user_input = discovery_info

        # Fetch available devices from Signal API
        self._available_devices, error_key = await fetch_available_devices(
            self.hass,
            self._user_input[CONF_SIGNAL_CLI_REST_API_URL],
            self._user_input[CONF_PHONE_NUMBER],
            self._available_devices or None,
        )
        if error_key:
            errors["base"] = error_key

        if user_input is not None:
            # User has selected devices
            approved_devices = user_input.get(CONF_APPROVED_DEVICES, [])

            # Add approved devices to config
            final_data = {**self._user_input, CONF_APPROVED_DEVICES: approved_devices}

            return self.async_create_entry(
                title=self._user_input.get(CONF_NAME, "Signal Gateway"),
                data=final_data,
            )

        # Show device selection form
        if not self._available_devices:
            # No devices found or connection error - create entry without devices
            return self.async_create_entry(
                title=self._user_input.get(CONF_NAME, "Signal Gateway"),
                data={**self._user_input, CONF_APPROVED_DEVICES: []},
            )

        # Build schema for device selection
        schema = build_device_selection_schema(self._available_devices)

        return self.async_show_form(
            step_id="discovery",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._available_devices))
            },
        )
