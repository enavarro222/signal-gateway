"""Validation logic for Signal Gateway configuration."""

import logging
from typing import Any

import voluptuous as vol
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

from ..const import CONF_SIGNAL_CLI_REST_API_URL, DOMAIN

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
    # Validate URL using Home Assistant's built-in validator
    try:
        api_url = user_input.get(CONF_SIGNAL_CLI_REST_API_URL, "")
        cv.url(api_url)  # Validates format and scheme (http/https)
    except (vol.Invalid, vol.MultipleInvalid) as err:
        raise ValueError(f"Invalid API URL: {err}") from err

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
