"""Tests for device_action module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_DEVICE_ID, CONF_TYPE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.signal_gateway.device_action import (
    ACTION_SEND_MESSAGE,
    async_get_actions,
    async_call_action_from_config,
)
from custom_components.signal_gateway.const import DOMAIN


@pytest.fixture
def mock_device_registry():
    """Mock device registry."""
    registry = MagicMock()
    device = MagicMock()
    device.identifiers = {(DOMAIN, "test_entry_contact_+33612345678")}
    device.name = "Test Contact"
    device.id = "test_device_id"
    registry.async_get.return_value = device
    return registry


@pytest.fixture
def mock_entity_registry():
    """Mock entity registry."""
    registry = MagicMock()
    entity = MagicMock()
    entity.entity_id = "notify.signal_test_contact_33612345678"
    entity.platform = DOMAIN
    entity.domain = "notify"
    entity.device_id = "test_device_id"

    # Mock the get_entries_for_device_id method
    registry.entities.get_entries_for_device_id.return_value = [entity]
    return registry


@pytest.mark.asyncio
async def test_async_get_actions(mock_device_registry):
    """Test async_get_actions returns send_message action."""
    hass = MagicMock(spec=HomeAssistant)

    with patch(
        "custom_components.signal_gateway.device_action.dr.async_get",
        return_value=mock_device_registry,
    ):
        actions = await async_get_actions(hass, "test_device_id")

    assert len(actions) == 1
    assert actions[0][CONF_TYPE] == ACTION_SEND_MESSAGE
    assert actions[0]["domain"] == DOMAIN


@pytest.mark.asyncio
async def test_async_get_actions_no_device():
    """Test async_get_actions returns empty list for non-existent device."""
    hass = MagicMock(spec=HomeAssistant)
    registry = MagicMock()
    registry.async_get.return_value = None

    with patch(
        "custom_components.signal_gateway.device_action.dr.async_get",
        return_value=registry,
    ):
        actions = await async_get_actions(hass, "non_existent_device")

    assert actions == []


@pytest.mark.asyncio
async def test_async_call_action_from_config(
    mock_device_registry, mock_entity_registry
):
    """Test async_call_action_from_config sends message."""
    hass = MagicMock(spec=HomeAssistant)
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()

    # Mock template rendering
    message_template = MagicMock()
    message_template.async_render.return_value = "Test message"

    config = {
        CONF_TYPE: ACTION_SEND_MESSAGE,
        CONF_DEVICE_ID: "test_device_id",
        "message": message_template,
    }

    with patch(
        "custom_components.signal_gateway.device_action.dr.async_get",
        return_value=mock_device_registry,
    ), patch(
        "custom_components.signal_gateway.device_action.er.async_get",
        return_value=mock_entity_registry,
    ):
        await async_call_action_from_config(hass, config, {}, None)

    # Verify service was called
    hass.services.async_call.assert_called_once()
    call_args = hass.services.async_call.call_args
    assert call_args[0][0] == "notify"
    assert call_args[0][1] == "send_message"
    assert call_args[0][2]["message"] == "Test message"
    assert "entity_id" in call_args[0][2]
