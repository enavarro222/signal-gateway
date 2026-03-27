"""Config and Options flows for Signal Gateway integration."""

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import (
    CONF_APPROVED_DEVICES,
    CONF_PHONE_NUMBER,
    CONF_SIGNAL_CLI_REST_API_URL,
    DOMAIN,
)
from .discovery import discover_devices
from .schema import build_signal_gateway_schema
from .validation import DuplicateServiceNameError, validate_signal_gateway_input

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
        if not self._available_devices:
            try:
                session = async_get_clientsession(self.hass)
                self._available_devices = await discover_devices(
                    self.hass,
                    self._user_input[CONF_SIGNAL_CLI_REST_API_URL],
                    self._user_input[CONF_PHONE_NUMBER],
                    session,
                )
            except aiohttp.ClientError as err:
                # Network/API error - show user-friendly message
                _LOGGER.error("Cannot connect to Signal API: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                # Unexpected error (e.g. data parsing) - show generic error
                # This is a safety net, should rarely happen
                _LOGGER.exception("Unexpected error fetching devices: %s", err)
                errors["base"] = "unknown"

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
        schema = vol.Schema(
            {
                vol.Optional(CONF_APPROVED_DEVICES, default=[]): cv.multi_select(
                    self._available_devices
                ),
            }
        )

        return self.async_show_form(
            step_id="discovery",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._available_devices))
            },
        )


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
        if not self._available_devices:
            try:
                session = async_get_clientsession(self.hass)
                self._available_devices = await discover_devices(
                    self.hass,
                    self._user_input[CONF_SIGNAL_CLI_REST_API_URL],
                    self._user_input[CONF_PHONE_NUMBER],
                    session,
                )
            except aiohttp.ClientError as err:
                # Network/API error - show user-friendly message
                _LOGGER.error("Cannot connect to Signal API: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:  # pylint: disable=broad-except
                # Unexpected error (e.g. data parsing) - show generic error
                # This is a safety net, should rarely happen
                _LOGGER.exception(
                    "Unexpected error fetching devices in options: %s", err
                )
                errors["base"] = "unknown"

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
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_APPROVED_DEVICES, default=current_approved
                ): cv.multi_select(self._available_devices),
            }
        )

        return self.async_show_form(
            step_id="discovery",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device_count": str(len(self._available_devices))
            },
        )
