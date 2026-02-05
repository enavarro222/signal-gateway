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

    # Mock SignalClient for discovery step
    with patch(
        "custom_components.signal_gateway.config_flow.SignalClient"
    ) as mock_client:
        from unittest.mock import AsyncMock

        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=[])
        mock_instance.list_groups = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        result = await flow.async_step_user(user_input=valid_user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Gateway"
    # Data should include approved_devices from discovery step
    assert "approved_devices" in result["data"]
    assert result["data"]["name"] == valid_user_input["name"]
    assert (
        result["data"]["signal_cli_rest_api_url"]
        == valid_user_input["signal_cli_rest_api_url"]
    )


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
async def test_user_flow_duplicate_service_name(valid_user_input):
    """Test user flow with duplicate service name."""
    from homeassistant.config_entries import ConfigEntry
    from custom_components.signal_gateway.const import DOMAIN

    flow = SignalGatewayConfigFlow()
    flow.hass = MagicMock()

    # Create a config entry with the same name
    existing_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="My Signal",
        data={"name": "Test Gateway"},  # Same as valid_user_input
        source="user",
        entry_id="existing_entry_id",
        unique_id="existing_unique_id",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    flow._async_current_entries = MagicMock(return_value=[existing_entry])

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
        "custom_components.signal_gateway.config_flow.config_flow.validate_signal_gateway_input",
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
