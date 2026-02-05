"""Tests for device_trigger module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_DEVICE_ID, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import Event, HomeAssistant

from custom_components.signal_gateway.device_trigger import (
    TRIGGER_MESSAGE_RECEIVED,
    async_get_triggers,
    async_attach_trigger,
    async_get_trigger_capabilities,
)
from custom_components.signal_gateway.const import DOMAIN, EVENT_SIGNAL_RECEIVED


@pytest.fixture
def mock_contact_device():
    """Mock contact device."""
    device = MagicMock()
    device.identifiers = {(DOMAIN, "test_entry_contact_+33612345678")}
    device.name = "Test Contact"
    device.id = "test_contact_device_id"
    return device


@pytest.fixture
def mock_group_device():
    """Mock group device."""
    device = MagicMock()
    device.identifiers = {
        (DOMAIN, "test_entry_group_id-123"),
        (DOMAIN, "test_entry_group-internal_internal-abc"),
    }
    device.name = "Test Group"
    device.id = "test_group_device_id"
    return device


@pytest.mark.asyncio
async def test_async_get_triggers_for_contact(mock_contact_device):
    """Test async_get_triggers returns message_received trigger for contact."""
    hass = MagicMock(spec=HomeAssistant)

    with patch(
        "custom_components.signal_gateway.device_trigger.async_get_signal_device",
        return_value=mock_contact_device,
    ):
        triggers = await async_get_triggers(hass, "test_contact_device_id")

    assert len(triggers) == 1
    assert triggers[0][CONF_PLATFORM] == "device"
    assert triggers[0][CONF_TYPE] == TRIGGER_MESSAGE_RECEIVED
    assert triggers[0][CONF_DEVICE_ID] == "test_contact_device_id"


@pytest.mark.asyncio
async def test_async_get_triggers_for_group(mock_group_device):
    """Test async_get_triggers returns message_received trigger for group."""
    hass = MagicMock(spec=HomeAssistant)

    with patch(
        "custom_components.signal_gateway.device_trigger.async_get_signal_device",
        return_value=mock_group_device,
    ):
        triggers = await async_get_triggers(hass, "test_group_device_id")

    assert len(triggers) == 1
    assert triggers[0][CONF_PLATFORM] == "device"
    assert triggers[0][CONF_TYPE] == TRIGGER_MESSAGE_RECEIVED


@pytest.mark.asyncio
async def test_async_get_triggers_device_not_found():
    """Test async_get_triggers returns empty list for unknown device."""
    hass = MagicMock(spec=HomeAssistant)

    with patch(
        "custom_components.signal_gateway.device_trigger.async_get_signal_device",
        return_value=None,
    ):
        triggers = await async_get_triggers(hass, "unknown_device_id")

    assert triggers == []


@pytest.mark.asyncio
async def test_async_attach_trigger_contact_message_with_data(
    mock_hass_with_bus, mock_contact_device
):
    """Test trigger fires for contact message with all message data."""
    action = AsyncMock()
    config = {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: "test_contact_device_id",
        CONF_TYPE: TRIGGER_MESSAGE_RECEIVED,
    }

    # Mock device registry
    device_registry = MagicMock()
    device_registry.async_get.return_value = mock_contact_device

    with patch(
        "custom_components.signal_gateway.device_trigger.dr.async_get",
        return_value=device_registry,
    ):
        detach = await async_attach_trigger(mock_hass_with_bus, config, action, {})

    # Verify listener was attached
    assert mock_hass_with_bus.bus.async_listen.called
    event_type, handler = mock_hass_with_bus.bus.async_listen.call_args[0]
    assert event_type == EVENT_SIGNAL_RECEIVED

    # Simulate event with message data
    event_data = {
        "envelope": {
            "source": "+33612345678",
            "dataMessage": {
                "message": "Hello from test!",
                "timestamp": 1234567890,
                "attachments": [{"contentType": "image/jpeg", "filename": "test.jpg"}],
            },
        }
    }
    event = Event(EVENT_SIGNAL_RECEIVED, event_data)

    await handler(event)

    # Verify action was called with message data
    assert action.called
    trigger_data = action.call_args[0][0]
    assert trigger_data["trigger"]["message"] == "Hello from test!"
    assert trigger_data["trigger"]["sender"] == "+33612345678"
    assert trigger_data["trigger"]["timestamp"] == 1234567890
    assert len(trigger_data["trigger"]["attachments"]) == 1
    assert trigger_data["trigger"]["attachments"][0]["contentType"] == "image/jpeg"
    assert trigger_data["trigger"]["envelope"] == event_data["envelope"]
    assert trigger_data["trigger"]["description"] == "Message from Test Contact"


@pytest.mark.asyncio
async def test_async_attach_trigger_contact_wrong_sender(
    mock_hass_with_bus, mock_contact_device
):
    """Test trigger does not fire for messages from other contacts."""
    hass = MagicMock(spec=HomeAssistant)
    action = AsyncMock()
    config = {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: "test_contact_device_id",
        CONF_TYPE: TRIGGER_MESSAGE_RECEIVED,
    }

    device_registry = MagicMock()
    device_registry.async_get.return_value = mock_contact_device

    with patch(
        "custom_components.signal_gateway.device_trigger.dr.async_get",
        return_value=device_registry,
    ):
        detach = await async_attach_trigger(mock_hass_with_bus, config, action, {})

    handler = mock_hass_with_bus.bus.async_listen.call_args[0][1]

    # Event from different contact
    event_data = {
        "envelope": {
            "source": "+9999999999",
            "dataMessage": {"message": "Hello"},
        }
    }
    event = Event(EVENT_SIGNAL_RECEIVED, event_data)

    await handler(event)

    # Action should not be called
    assert not action.called


@pytest.mark.asyncio
async def test_async_attach_trigger_group_message_with_data(
    mock_hass_with_bus, mock_group_device
):
    """Test trigger fires for group message with all message data."""
    action = AsyncMock()
    config = {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: "test_group_device_id",
        CONF_TYPE: TRIGGER_MESSAGE_RECEIVED,
    }

    device_registry = MagicMock()
    device_registry.async_get.return_value = mock_group_device

    with patch(
        "custom_components.signal_gateway.device_trigger.dr.async_get",
        return_value=device_registry,
    ):
        detach = await async_attach_trigger(mock_hass_with_bus, config, action, {})

    handler = mock_hass_with_bus.bus.async_listen.call_args[0][1]

    # Simulate group message with metadata
    event_data = {
        "envelope": {
            "source": "+33612345678",
            "dataMessage": {
                "message": "Group message!",
                "timestamp": 9876543210,
                "attachments": [],
                "groupInfo": {
                    "groupId": "internal-abc",
                    "type": "DELIVER",
                },
            },
        }
    }
    event = Event(EVENT_SIGNAL_RECEIVED, event_data)

    await handler(event)

    # Verify action was called with message data
    assert action.called
    trigger_data = action.call_args[0][0]
    assert trigger_data["trigger"]["message"] == "Group message!"
    assert trigger_data["trigger"]["sender"] == "+33612345678"
    assert trigger_data["trigger"]["timestamp"] == 9876543210
    assert trigger_data["trigger"]["attachments"] == []
    assert trigger_data["trigger"]["group_info"]["groupId"] == "internal-abc"
    assert trigger_data["trigger"]["envelope"] == event_data["envelope"]
    assert trigger_data["trigger"]["description"] == "Message in Test Group"


@pytest.mark.asyncio
async def test_async_attach_trigger_group_wrong_group(
    mock_hass_with_bus, mock_group_device
):
    """Test trigger does not fire for messages in other groups."""
    action = AsyncMock()
    config = {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: "test_group_device_id",
        CONF_TYPE: TRIGGER_MESSAGE_RECEIVED,
    }

    device_registry = MagicMock()
    device_registry.async_get.return_value = mock_group_device

    with patch(
        "custom_components.signal_gateway.device_trigger.dr.async_get",
        return_value=device_registry,
    ):
        detach = await async_attach_trigger(mock_hass_with_bus, config, action, {})

    handler = mock_hass_with_bus.bus.async_listen.call_args[0][1]

    # Event from different group
    event_data = {
        "envelope": {
            "source": "+33612345678",
            "dataMessage": {
                "message": "Message",
                "groupInfo": {"groupId": "different-group-id"},
            },
        }
    }
    event = Event(EVENT_SIGNAL_RECEIVED, event_data)

    await handler(event)

    # Action should not be called
    assert not action.called


@pytest.mark.asyncio
async def test_async_attach_trigger_unknown_type(mock_hass_with_bus):
    """Test attach trigger with unknown trigger type."""
    action = AsyncMock()
    config = {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: "test_device_id",
        CONF_TYPE: "unknown_type",
    }

    detach = await async_attach_trigger(mock_hass_with_bus, config, action, {})

    # Should return a no-op function
    assert callable(detach)
    detach()  # Should not raise


@pytest.mark.asyncio
async def test_async_attach_trigger_device_not_found(mock_hass_with_bus):
    """Test attach trigger when device is not found."""
    action = AsyncMock()
    config = {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: "unknown_device_id",
        CONF_TYPE: TRIGGER_MESSAGE_RECEIVED,
    }

    device_registry = MagicMock()
    device_registry.async_get.return_value = None

    with patch(
        "custom_components.signal_gateway.device_trigger.dr.async_get",
        return_value=device_registry,
    ):
        detach = await async_attach_trigger(mock_hass_with_bus, config, action, {})

    # Should return a no-op function
    assert callable(detach)
    detach()  # Should not raise


@pytest.mark.asyncio
async def test_async_attach_trigger_message_without_data(mock_hass_with_bus):
    """Test trigger handles messages with minimal data."""
    action = AsyncMock()
    config = {
        CONF_PLATFORM: "device",
        CONF_DEVICE_ID: "test_contact_device_id",
        CONF_TYPE: TRIGGER_MESSAGE_RECEIVED,
    }

    device = MagicMock()
    device.identifiers = {(DOMAIN, "test_entry_contact_+33612345678")}
    device.name = "Test Contact"

    device_registry = MagicMock()
    device_registry.async_get.return_value = device

    with patch(
        "custom_components.signal_gateway.device_trigger.dr.async_get",
        return_value=device_registry,
    ):
        detach = await async_attach_trigger(mock_hass_with_bus, config, action, {})

    handler = mock_hass_with_bus.bus.async_listen.call_args[0][1]

    # Event with minimal data
    event_data = {
        "envelope": {
            "source": "+33612345678",
            "dataMessage": {},  # Empty data message
        }
    }
    event = Event(EVENT_SIGNAL_RECEIVED, event_data)

    await handler(event)

    # Verify action was called with empty/default values
    assert action.called
    trigger_data = action.call_args[0][0]
    assert trigger_data["trigger"]["message"] == ""
    assert trigger_data["trigger"]["sender"] == "+33612345678"
    assert trigger_data["trigger"]["timestamp"] is None
    assert trigger_data["trigger"]["attachments"] == []


@pytest.mark.asyncio
async def test_async_get_trigger_capabilities():
    """Test async_get_trigger_capabilities returns empty dict."""
    hass = MagicMock(spec=HomeAssistant)
    config = {}

    capabilities = await async_get_trigger_capabilities(hass, config)

    assert capabilities == {}
