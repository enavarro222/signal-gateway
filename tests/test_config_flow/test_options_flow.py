"""Tests for SignalGatewayOptionsFlow."""

import pytest
from unittest.mock import MagicMock, patch

from homeassistant.data_entry_flow import FlowResultType

from custom_components.signal_gateway.config_flow import SignalGatewayOptionsFlow
from custom_components.signal_gateway.const import DOMAIN


@pytest.mark.asyncio
async def test_options_flow_init_show_form(mock_config_entry):
    """Test showing the options form."""
    flow = SignalGatewayOptionsFlow(mock_config_entry)
    flow.hass = MagicMock()

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_options_flow_success(valid_user_input, mock_config_entry):
    """Test successful options flow."""
    flow = SignalGatewayOptionsFlow(mock_config_entry)

    mock_hass = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
    mock_hass.config_entries.async_update_entry = MagicMock()
    flow.hass = mock_hass

    result = await flow.async_step_init(user_input=valid_user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    mock_hass.config_entries.async_update_entry.assert_called_once_with(
        mock_config_entry, data=valid_user_input
    )


@pytest.mark.asyncio
async def test_options_flow_invalid_url(valid_user_input, mock_config_entry):
    """Test options flow with invalid URL."""
    flow = SignalGatewayOptionsFlow(mock_config_entry)

    mock_hass = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[])
    flow.hass = mock_hass

    invalid_input = valid_user_input.copy()
    invalid_input["signal_cli_rest_api_url"] = "invalid"

    result = await flow.async_step_init(user_input=invalid_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_url"


@pytest.mark.asyncio
async def test_options_flow_duplicate_service_name(valid_user_input, mock_config_entry):
    """Test options flow with duplicate service name."""
    flow = SignalGatewayOptionsFlow(mock_config_entry)

    # Create another entry with the same name
    other_entry = MagicMock()
    other_entry.entry_id = "other_entry_id"
    other_entry.data = {"name": "My Signal"}  # Same as valid_user_input

    mock_hass = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(
        return_value=[mock_config_entry, other_entry]
    )
    flow.hass = mock_hass

    result = await flow.async_step_init(user_input=valid_user_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "duplicate_service_name"


@pytest.mark.asyncio
async def test_options_flow_exclude_current_entry(valid_user_input, mock_config_entry):
    """Test that current entry is excluded from duplicate check."""
    flow = SignalGatewayOptionsFlow(mock_config_entry)

    # Use the same name as current entry - should be allowed
    input_with_same_name = valid_user_input.copy()
    input_with_same_name["name"] = mock_config_entry.data["name"]

    mock_hass = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[mock_config_entry])
    mock_hass.config_entries.async_update_entry = MagicMock()
    flow.hass = mock_hass

    result = await flow.async_step_init(user_input=input_with_same_name)

    assert result["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_options_flow_unknown_error(valid_user_input, mock_config_entry):
    """Test options flow with unknown error."""
    flow = SignalGatewayOptionsFlow(mock_config_entry)

    mock_hass = MagicMock()
    mock_hass.config_entries.async_entries = MagicMock(return_value=[])
    flow.hass = mock_hass

    # Mock validation to raise unexpected error
    with patch(
        "custom_components.signal_gateway.config_flow.validate_signal_gateway_input",
        side_effect=Exception("Unexpected error"),
    ):
        result = await flow.async_step_init(user_input=valid_user_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


@pytest.mark.asyncio
async def test_options_flow_uses_current_config_as_defaults(mock_config_entry):
    """Test that current configuration is used as defaults."""
    flow = SignalGatewayOptionsFlow(mock_config_entry)
    flow.hass = MagicMock()

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    # Schema should be built with current config entry data as defaults
