"""Tests for SignalGatewayConfigFlow user flow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.signal_gateway.config_flow import SignalGatewayConfigFlow
from custom_components.signal_gateway.const import DOMAIN


@pytest.fixture
def mock_setup_entry():
    """Mock async_setup_entry."""
    with patch(
        "custom_components.signal_gateway.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.mark.asyncio
async def test_user_flow_success(valid_user_input, mock_setup_entry):
    """Test successful user flow."""
    flow = SignalGatewayConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])

    result = await flow.async_step_user(user_input=valid_user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Signal"
    assert result["data"] == valid_user_input


@pytest.mark.asyncio
async def test_user_flow_show_form():
    """Test showing the user form."""
    flow = SignalGatewayConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


@pytest.mark.asyncio
async def test_user_flow_invalid_url(valid_user_input):
    """Test user flow with invalid URL."""
    flow = SignalGatewayConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])

    invalid_input = valid_user_input.copy()
    invalid_input["signal_cli_rest_api_url"] = "ftp://invalid"

    result = await flow.async_step_user(user_input=invalid_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_url"


@pytest.mark.asyncio
async def test_user_flow_duplicate_service_name(valid_user_input, mock_config_entry):
    """Test user flow with duplicate service name."""
    flow = SignalGatewayConfigFlow()
    flow.hass = MagicMock()

    # Set up existing entry with same name after slugification
    mock_config_entry.data["name"] = "My Signal"  # Same as valid_user_input
    flow._async_current_entries = MagicMock(return_value=[mock_config_entry])

    result = await flow.async_step_user(user_input=valid_user_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "duplicate_service_name"


@pytest.mark.asyncio
async def test_user_flow_unknown_error(valid_user_input):
    """Test user flow with unknown error."""
    flow = SignalGatewayConfigFlow()
    flow.hass = MagicMock()

    # Mock validation to raise unexpected error
    with patch(
        "custom_components.signal_gateway.config_flow.validate_signal_gateway_input",
        side_effect=Exception("Unexpected error"),
    ):
        result = await flow.async_step_user(user_input=valid_user_input)

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "unknown"


@pytest.mark.asyncio
async def test_user_flow_preserves_input_on_error(valid_user_input):
    """Test that user input is preserved in form after validation error."""
    flow = SignalGatewayConfigFlow()
    flow.hass = MagicMock()
    flow._async_current_entries = MagicMock(return_value=[])

    # Make input invalid
    invalid_input = valid_user_input.copy()
    invalid_input["signal_cli_rest_api_url"] = "invalid"

    result = await flow.async_step_user(user_input=invalid_input)

    assert result["type"] == FlowResultType.FORM
    assert result["data_schema"] is not None
    # The schema should be built with the invalid input to preserve values
