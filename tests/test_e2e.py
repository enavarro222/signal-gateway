"""End-to-end tests for Signal Gateway integration.

Tests the full integration lifecycle using Home Assistant's testing framework:
- Config entry setup
- Notify service registration
- Service calls
- WebSocket events
- Config entry reload/unload
"""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME
from homeassistant.setup import async_setup_component

from custom_components.signal_gateway.const import (
    DOMAIN,
    CONF_SIGNAL_CLI_REST_API_URL,
    CONF_PHONE_NUMBER,
    CONF_WEBSOCKET_ENABLED,
    EVENT_SIGNAL_RECEIVED,
)


@pytest.fixture
def mock_signal_client():
    """Mock SignalClient for e2e tests."""
    with patch("custom_components.signal_gateway.SignalClient") as mock_client_class:
        mock_client = MagicMock()
        mock_client.send_message = AsyncMock(return_value={"timestamp": 123456})
        mock_client.start_listening = AsyncMock()
        mock_client.stop_listening = AsyncMock()
        mock_client.set_message_handler = MagicMock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.mark.asyncio
async def test_full_integration_lifecycle(hass: HomeAssistant, mock_signal_client):
    """Test complete integration lifecycle: setup, service call, unload."""

    # Create config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "test_gateway",
            CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
            CONF_PHONE_NUMBER: "+33612345678",
            CONF_WEBSOCKET_ENABLED: False,
        },
        entry_id="test_entry_id",
        unique_id="test_gateway",
    )
    config_entry.add_to_hass(hass)

    # Setup integration
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify notify service is registered
    assert hass.services.has_service("notify", "test_gateway")

    # Call notify service
    await hass.services.async_call(
        "notify",
        "test_gateway",
        {"message": "Hello from e2e test", "target": "+33698765432"},
        blocking=True,
    )

    # Verify send_message was called
    mock_signal_client.send_message.assert_called_once()
    call_args = mock_signal_client.send_message.call_args
    assert call_args[1]["message"] == "Hello from e2e test"
    assert call_args[1]["target"] == "+33698765432"

    # Unload config entry
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify service is unregistered
    assert not hass.services.has_service("notify", "test_gateway")


@pytest.mark.asyncio
async def test_websocket_event_handling(hass: HomeAssistant, mock_signal_client):
    """Test WebSocket message reception and event firing."""

    # Track events
    events = []

    def event_listener(event):
        events.append(event)

    hass.bus.async_listen(EVENT_SIGNAL_RECEIVED, event_listener)

    # Create config entry with WebSocket enabled
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "test_gateway_ws",
            CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
            CONF_PHONE_NUMBER: "+33612345678",
            CONF_WEBSOCKET_ENABLED: True,
        },
        entry_id="test_entry_ws",
        unique_id="test_gateway_ws",
    )
    config_entry.add_to_hass(hass)

    # Setup integration
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify WebSocket was started
    mock_signal_client.start_listening.assert_called_once()

    # Get the message handler that was set
    mock_signal_client.set_message_handler.assert_called_once()
    message_handler = mock_signal_client.set_message_handler.call_args[0][0]
    assert message_handler is not None

    # Simulate incoming message
    incoming_message = {
        "envelope": {
            "source": "+33698765432",
            "sourceNumber": "+33698765432",
            "timestamp": 1234567890,
            "dataMessage": {
                "message": "Test message from Signal",
                "timestamp": 1234567890,
            },
        }
    }

    await message_handler(incoming_message)
    await hass.async_block_till_done()

    # Verify event was fired
    assert len(events) == 1
    event_data = events[0].data
    # Event data contains the raw message envelope
    assert "envelope" in event_data
    assert event_data["envelope"]["source"] == "+33698765432"
    assert (
        event_data["envelope"]["dataMessage"]["message"] == "Test message from Signal"
    )

    # Cleanup
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    mock_signal_client.stop_listening.assert_called_once()


@pytest.mark.asyncio
async def test_reload_config_entry(hass: HomeAssistant, mock_signal_client):
    """Test config entry reload preserves functionality."""

    # Create config entry
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "test_reload",
            CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
            CONF_PHONE_NUMBER: "+33612345678",
            CONF_WEBSOCKET_ENABLED: False,
        },
        entry_id="test_reload_id",
        unique_id="test_reload",
    )
    config_entry.add_to_hass(hass)

    # Initial setup
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service("notify", "test_reload")

    # Reload
    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()

    # Verify service still works after reload
    assert hass.services.has_service("notify", "test_reload")

    await hass.services.async_call(
        "notify",
        "test_reload",
        {"message": "After reload", "target": "+33698765432"},
        blocking=True,
    )

    # Verify the service was called after reload
    assert mock_signal_client.send_message.call_count == 1


@pytest.mark.asyncio
async def test_multiple_config_entries(hass: HomeAssistant, mock_signal_client):
    """Test multiple Signal Gateway instances can coexist."""

    # Create two config entries
    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "gateway1",
            CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8080",
            CONF_PHONE_NUMBER: "+33611111111",
            CONF_WEBSOCKET_ENABLED: False,
        },
        entry_id="entry1",
        unique_id="gateway1",
    )
    entry1.add_to_hass(hass)

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "gateway2",
            CONF_SIGNAL_CLI_REST_API_URL: "http://localhost:8081",
            CONF_PHONE_NUMBER: "+33622222222",
            CONF_WEBSOCKET_ENABLED: False,
        },
        entry_id="entry2",
        unique_id="gateway2",
    )
    entry2.add_to_hass(hass)

    # Setup both entries - HA will process them together
    await hass.config_entries.async_setup(entry1.entry_id)
    # Check if entry2 was already loaded (can happen when HA processes multiple entries)
    if entry2.state.name != "LOADED":
        await hass.config_entries.async_setup(entry2.entry_id)
    await hass.async_block_till_done()

    # Verify both services exist
    assert hass.services.has_service("notify", "gateway1")
    assert hass.services.has_service("notify", "gateway2")

    # Call both services
    await hass.services.async_call(
        "notify",
        "gateway1",
        {"message": "From gateway1", "target": "+33611111111"},
        blocking=True,
    )
    await hass.services.async_call(
        "notify",
        "gateway2",
        {"message": "From gateway2", "target": "+33622222222"},
        blocking=True,
    )

    # Verify both were called
    assert mock_signal_client.send_message.call_count == 2

    # Unload one entry
    assert await hass.config_entries.async_unload(entry1.entry_id)
    await hass.async_block_till_done()

    # Verify only gateway2 remains
    assert not hass.services.has_service("notify", "gateway1")
    assert hass.services.has_service("notify", "gateway2")

    # Cleanup
    assert await hass.config_entries.async_unload(entry2.entry_id)
    await hass.async_block_till_done()
