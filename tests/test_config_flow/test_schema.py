"""Tests for schema building functions."""

import voluptuous as vol

from custom_components.signal_gateway.config_flow import (
    build_signal_gateway_schema,
    build_device_selection_schema,
)
from custom_components.signal_gateway.const import (
    CONF_APPROVED_DEVICES,
    CONF_PHONE_NUMBER,
    CONF_RECIPIENTS,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_WEBSOCKET_ENABLED,
)
from homeassistant.const import CONF_NAME


def test_build_signal_gateway_schema_no_defaults():
    """Test building schema without defaults."""
    schema = build_signal_gateway_schema()

    assert isinstance(schema, vol.Schema)
    assert CONF_NAME in schema.schema
    assert CONF_SIGNAL_CLI_REST_API_URL in schema.schema
    assert CONF_PHONE_NUMBER in schema.schema
    assert CONF_WEBSOCKET_ENABLED in schema.schema
    assert CONF_RECIPIENTS in schema.schema


def test_build_signal_gateway_schema_with_defaults():
    """Test building schema with defaults."""
    defaults = {
        CONF_NAME: "Custom Signal",
        CONF_SIGNAL_CLI_REST_API_URL: "http://192.168.1.100:8080",
        CONF_PHONE_NUMBER: "+9876543210",
        CONF_WEBSOCKET_ENABLED: False,
        CONF_RECIPIENTS: "+1234567890",
    }

    schema = build_signal_gateway_schema(defaults)

    assert isinstance(schema, vol.Schema)
    # Schema should have the same fields
    assert CONF_NAME in schema.schema
    assert CONF_SIGNAL_CLI_REST_API_URL in schema.schema
    assert CONF_PHONE_NUMBER in schema.schema
    assert CONF_WEBSOCKET_ENABLED in schema.schema
    assert CONF_RECIPIENTS in schema.schema


def test_build_signal_gateway_schema_default_name():
    """Test that CONF_NAME has default value of 'Signal'."""
    schema = build_signal_gateway_schema()

    # Get the default for CONF_NAME field
    name_field = None
    for key in schema.schema:
        if hasattr(key, "schema") and key.schema == CONF_NAME:
            name_field = key
            break

    assert name_field is not None
    assert name_field.default() == "Signal"


def test_build_signal_gateway_schema_websocket_enabled_default():
    """Test that CONF_WEBSOCKET_ENABLED defaults to True."""
    schema = build_signal_gateway_schema()

    # Get the default for CONF_WEBSOCKET_ENABLED field
    websocket_field = None
    for key in schema.schema:
        if hasattr(key, "schema") and key.schema == CONF_WEBSOCKET_ENABLED:
            websocket_field = key
            break

    assert websocket_field is not None
    assert websocket_field.default() is True


def test_build_signal_gateway_schema_recipients_default():
    """Test that CONF_RECIPIENTS defaults to empty string."""
    schema = build_signal_gateway_schema()

    # Get the default for CONF_RECIPIENTS field
    recipients_field = None
    for key in schema.schema:
        if hasattr(key, "schema") and key.schema == CONF_RECIPIENTS:
            recipients_field = key
            break

    assert recipients_field is not None
    assert recipients_field.default() == ""


def test_build_signal_gateway_schema_required_fields():
    """Test that required fields are actually required."""
    schema = build_signal_gateway_schema()

    required_fields = []
    optional_fields = []

    for key in schema.schema:
        if hasattr(key, "schema"):
            if isinstance(key, vol.Required):
                required_fields.append(key.schema)
            elif isinstance(key, vol.Optional):
                optional_fields.append(key.schema)

    # These should be required
    assert CONF_SIGNAL_CLI_REST_API_URL in required_fields
    assert CONF_PHONE_NUMBER in required_fields

    # These should be optional
    assert CONF_NAME in optional_fields
    assert CONF_WEBSOCKET_ENABLED in optional_fields
    assert CONF_RECIPIENTS in optional_fields


def test_build_device_selection_schema_no_defaults():
    """Test building device selection schema without defaults."""
    available_devices = {
        "contact_+33612345678": "John Doe",
        "group_abc123": "Test Group",
    }

    schema = build_device_selection_schema(available_devices)

    assert isinstance(schema, vol.Schema)

    # Find the Optional field with CONF_APPROVED_DEVICES
    for key in schema.schema:
        if hasattr(key, "schema") and key.schema == CONF_APPROVED_DEVICES:
            # Check that default is empty list (default can be a callable)
            default_value = key.default() if callable(key.default) else key.default
            assert default_value == []
            return

    # If we get here, the field wasn't found
    assert False, "CONF_APPROVED_DEVICES not found in schema"


def test_build_device_selection_schema_with_defaults():
    """Test building device selection schema with default selections."""
    available_devices = {
        "contact_+33612345678": "John Doe",
        "group_abc123": "Test Group",
    }
    default_selected = ["contact_+33612345678"]

    schema = build_device_selection_schema(available_devices, default_selected)

    assert isinstance(schema, vol.Schema)

    # Find the Optional field with CONF_APPROVED_DEVICES
    for key in schema.schema:
        if hasattr(key, "schema") and key.schema == CONF_APPROVED_DEVICES:
            # Check that default is the provided list (default can be a callable)
            default_value = key.default() if callable(key.default) else key.default
            assert default_value == default_selected
            return

    # If we get here, the field wasn't found
    assert False, "CONF_APPROVED_DEVICES not found in schema"


def test_build_device_selection_schema_empty_devices():
    """Test building device selection schema with no available devices."""
    available_devices = {}

    schema = build_device_selection_schema(available_devices)

    assert isinstance(schema, vol.Schema)
    assert CONF_APPROVED_DEVICES in schema.schema


def test_build_device_selection_schema_field_is_optional():
    """Test that approved_devices field is optional."""
    available_devices = {"contact_+33612345678": "John Doe"}
    schema = build_device_selection_schema(available_devices)

    # Find the field in schema
    is_optional = False
    for key in schema.schema:
        if hasattr(key, "schema") and key.schema == CONF_APPROVED_DEVICES:
            if isinstance(key, vol.Optional):
                is_optional = True

    assert is_optional
