"""Tests for validation functions."""

import pytest
from homeassistant.const import CONF_NAME
from unittest.mock import MagicMock

from custom_components.signal_gateway.config_flow import (
    validate_signal_gateway_input,
    DuplicateServiceNameError,
)
from custom_components.signal_gateway.const import (
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
    DOMAIN,
)


def test_validate_signal_gateway_input_valid(valid_user_input):
    """Test validation with valid input."""
    # Should not raise any exception
    validate_signal_gateway_input(valid_user_input, [])


def test_validate_signal_gateway_input_no_url():
    """Test validation with missing URL."""
    user_input = {
        CONF_NAME: "Test",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    with pytest.raises(ValueError, match="Invalid API URL"):
        validate_signal_gateway_input(user_input, [])


def test_validate_signal_gateway_input_empty_url():
    """Test validation with empty URL."""
    user_input = {
        CONF_NAME: "Test",
        CONF_SIGNAL_CLI_REST_API_URL: "",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    with pytest.raises(ValueError, match="Invalid API URL"):
        validate_signal_gateway_input(user_input, [])


def test_validate_signal_gateway_input_invalid_url_scheme():
    """Test validation with invalid URL scheme."""
    user_input = {
        CONF_NAME: "Test",
        CONF_SIGNAL_CLI_REST_API_URL: "ftp://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    with pytest.raises(ValueError, match="Invalid API URL"):
        validate_signal_gateway_input(user_input, [])


def test_validate_signal_gateway_input_duplicate_name_default():
    """Test validation with duplicate default name."""
    user_input = {
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    # Create existing entry with default name
    existing_entry = MagicMock()
    existing_entry.entry_id = "existing_id"
    existing_entry.data = {CONF_SIGNAL_CLI_REST_API_URL: "http://other:8080"}

    with pytest.raises(DuplicateServiceNameError):
        validate_signal_gateway_input(user_input, [existing_entry])


def test_validate_signal_gateway_input_duplicate_name_custom():
    """Test validation with duplicate custom name."""
    user_input = {
        CONF_NAME: "My Signal Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    # Create existing entry with same name
    existing_entry = MagicMock()
    existing_entry.entry_id = "existing_id"
    existing_entry.data = {
        CONF_NAME: "My Signal Gateway",
        CONF_SIGNAL_CLI_REST_API_URL: "http://other:8080",
    }

    with pytest.raises(DuplicateServiceNameError):
        validate_signal_gateway_input(user_input, [existing_entry])


def test_validate_signal_gateway_input_duplicate_name_slugified():
    """Test validation with duplicate name after slugification."""
    user_input = {
        CONF_NAME: "My Signal!",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    # Create existing entry with similar name that slugifies to the same
    existing_entry = MagicMock()
    existing_entry.entry_id = "existing_id"
    existing_entry.data = {
        CONF_NAME: "My Signal",  # Slugifies to my_signal, same as "My Signal!"
        CONF_SIGNAL_CLI_REST_API_URL: "http://other:8080",
    }

    with pytest.raises(DuplicateServiceNameError):
        validate_signal_gateway_input(user_input, [existing_entry])


def test_validate_signal_gateway_input_exclude_current_entry():
    """Test validation excluding current entry from duplicate check."""
    user_input = {
        CONF_NAME: "Test Signal",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    # Create existing entry with same name but will be excluded
    existing_entry = MagicMock()
    existing_entry.entry_id = "test_entry_id"
    existing_entry.data = {
        CONF_NAME: "Test Signal",
        CONF_SIGNAL_CLI_REST_API_URL: "http://other:8080",
    }

    # Should not raise because we exclude this entry
    validate_signal_gateway_input(
        user_input, [existing_entry], exclude_entry_id="test_entry_id"
    )


def test_validate_signal_gateway_input_different_names():
    """Test validation with different names (no conflict)."""
    user_input = {
        CONF_NAME: "New Signal",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    # Create existing entry with different name
    existing_entry = MagicMock()
    existing_entry.entry_id = "existing_id"
    existing_entry.data = {
        CONF_NAME: "Old Signal",
        CONF_SIGNAL_CLI_REST_API_URL: "http://other:8080",
    }

    # Should not raise
    validate_signal_gateway_input(user_input, [existing_entry])


def test_validate_signal_gateway_input_http_url():
    """Test validation with http URL."""
    user_input = {
        CONF_NAME: "Test",
        CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    validate_signal_gateway_input(user_input, [])


def test_validate_signal_gateway_input_https_url():
    """Test validation with https URL."""
    user_input = {
        CONF_NAME: "Test",
        CONF_SIGNAL_CLI_REST_API_URL: "https://signal.example.com:8443",
        CONF_PHONE_NUMBER: "+1234567890",
    }

    validate_signal_gateway_input(user_input, [])
