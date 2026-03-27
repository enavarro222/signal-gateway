"""Options flow for Signal Gateway integration."""

# pylint: disable=duplicate-code
# ConfigFlow and OptionsFlow share similar structure by design (async_step_discovery).
# They inherit from different base classes and have different responsibilities,
# making abstraction impractical. This duplication is intentional and acceptable.

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlowResult, OptionsFlow

from ..const import (
    CONF_APPROVED_DEVICES,
    CONF_PHONE_NUMBER,
    CONF_SIGNAL_CLI_REST_API_URL,
    DOMAIN,
)
from .discovery import fetch_available_devices
from .schema import build_signal_gateway_schema, build_device_selection_schema
from .validation import DuplicateServiceNameError, validate_signal_gateway_input

_LOGGER = logging.getLogger(__name__)


class SignalGatewayOptionsFlow(OptionsFlow):
    """Handle options flow for Signal Gateway."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry
        self._user_input: dict[str, Any] = {}
        self._available_devices: dict[str, Any] = {}

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
                # Store user input and proceed to discovery step
                self._user_input = user_input
                return await self.async_step_discovery()

        # Get current configuration or user_input if validation failed
        defaults = user_input if user_input else self._config_entry.data

        return self.async_show_form(
            step_id="init",
            data_schema=build_signal_gateway_schema(defaults),
            errors=errors,
        )

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle device discovery step in options flow."""
        errors: dict[str, str] = {}

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

            # Update the config entry with new data
            final_data = {**self._user_input, CONF_APPROVED_DEVICES: approved_devices}
            self.hass.config_entries.async_update_entry(
                self._config_entry, data=final_data
            )
            return self.async_create_entry(title="", data={})

        # Show device selection form
        if not self._available_devices:
            # No devices found or connection error - update without changing devices
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                data={
                    **self._user_input,
                    CONF_APPROVED_DEVICES: self._config_entry.data.get(
                        CONF_APPROVED_DEVICES, []
                    ),
                },
            )
            return self.async_create_entry(title="", data={})

        # Get currently approved devices as default
        current_approved = self._config_entry.data.get(CONF_APPROVED_DEVICES, [])

        # Build schema for device selection
        schema = build_device_selection_schema(
            self._available_devices, current_approved
        )

        return self.async_show_form(
            step_id="discovery",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._available_devices))
            },
        )
