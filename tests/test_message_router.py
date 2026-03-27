"""Tests for SignalMessageRouter."""

# pylint: disable=redefined-outer-name,protected-access

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.signal_gateway.coordinator import SignalGroupCoordinator
from custom_components.signal_gateway.data import SignalGatewayEntryData
from custom_components.signal_gateway.message_router import SignalMessageRouter
from custom_components.signal_gateway.const import (
    DOMAIN,
    EVENT_SIGNAL_RECEIVED,
    EVENT_TYPING_INDICATOR,
)


@pytest.fixture
def message_router(mock_hass, mock_entry, mock_signal_client):
    """Create a SignalMessageRouter instance."""
    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
    )
    return SignalMessageRouter(
        hass=mock_hass,
        entry=mock_entry,
        client=mock_signal_client,
    )


@pytest.fixture
def received_message_data():
    """Sample received message data from websocket."""
    return {
        "envelope": {
            "source": "+1234567890",
            "sourceNumber": "+1234567890",
            "sourceUuid": "test-uuid",
            "sourceName": "John Doe",
            "sourceDevice": 1,
            "timestamp": 1234567890000,
            "dataMessage": {
                "timestamp": 1234567890000,
                "message": "Hello from Signal!",
                "expiresInSeconds": 0,
                "viewOnce": False,
            },
        },
        "account": "+9876543210",
    }


@pytest.fixture
def group_update_message_data():
    """Sample group update message data from websocket."""
    return {
        "envelope": {
            "source": "+1234567890",
            "sourceNumber": "+1234567890",
            "sourceUuid": "test-uuid",
            "timestamp": 1234567890000,
            "dataMessage": {
                "timestamp": 1234567890000,
                "groupInfo": {
                    "type": "UPDATE",
                    "groupId": "internal-group-id-123",
                    "revision": 5,
                },
            },
        },
        "account": "+9876543210",
    }


@pytest.fixture
def typing_indicator_data():
    """Sample typing indicator data (contact, not group)."""
    return {
        "envelope": {
            "source": "+1234567890",
            "sourceNumber": "+1234567890",
            "sourceUuid": "test-uuid",
            "timestamp": 1234567890000,
            "typingMessage": {
                "action": "STARTED",
                "timestamp": 1234567890000,
            },
        },
        "account": "+9876543210",
    }


@pytest.fixture
def group_typing_indicator_data():
    """Sample group typing indicator data (should be ignored)."""
    return {
        "envelope": {
            "source": "+1234567890",
            "sourceNumber": "+1234567890",
            "sourceUuid": "test-uuid",
            "timestamp": 1234567890000,
            "typingMessage": {
                "action": "STARTED",
                "timestamp": 1234567890000,
                "groupId": "group-internal-id",
            },
        },
        "account": "+9876543210",
    }


@pytest.fixture
def unrecognized_message_data():
    """Sample unrecognized message data."""
    return {
        "envelope": {
            "source": "+1234567890",
            "sourceNumber": "+1234567890",
            "timestamp": 1234567890000,
            "receiptMessage": {
                "when": 1234567890000,
                "isDelivery": True,
                "isRead": False,
                "timestamps": [1234567890000],
            },
        },
        "account": "+9876543210",
    }


# Test classify_message


def test_classify_message_received_message(message_router, received_message_data):
    """Test classify_message identifies received message correctly."""
    msg_type = message_router.classify_message(received_message_data)
    assert msg_type == "received_message"


def test_classify_message_group_update(message_router, group_update_message_data):
    """Test classify_message identifies group update correctly."""
    msg_type = message_router.classify_message(group_update_message_data)
    assert msg_type == "group_update"


def test_classify_message_typing_indicator_contact(
    message_router, typing_indicator_data
):
    """Test classify_message identifies contact typing indicator correctly."""
    msg_type = message_router.classify_message(typing_indicator_data)
    assert msg_type == "typing_indicator"


def test_classify_message_typing_indicator_group(
    message_router, group_typing_indicator_data
):
    """Test classify_message ignores group typing indicators."""
    msg_type = message_router.classify_message(group_typing_indicator_data)
    assert msg_type is None


def test_classify_message_unrecognized(message_router, unrecognized_message_data):
    """Test classify_message returns None for unrecognized messages."""
    msg_type = message_router.classify_message(unrecognized_message_data)
    assert msg_type is None


def test_classify_message_empty_envelope(message_router):
    """Test classify_message handles empty envelope gracefully."""
    msg_type = message_router.classify_message({"envelope": {}})
    assert msg_type is None


def test_classify_message_no_envelope(message_router):
    """Test classify_message handles missing envelope gracefully."""
    msg_type = message_router.classify_message({})
    assert msg_type is None


def test_classify_message_data_message_without_text(message_router):
    """Test classify_message handles data message without text content."""
    msg = {
        "envelope": {
            "dataMessage": {
                "timestamp": 1234567890000,
                # No "message" field
                "expiresInSeconds": 0,
            },
        },
    }
    msg_type = message_router.classify_message(msg)
    assert msg_type is None


def test_classify_message_group_update_without_id(message_router):
    """Test classify_message handles group update without group ID."""
    msg = {
        "envelope": {
            "dataMessage": {
                "groupInfo": {
                    "type": "UPDATE",
                    # No groupId field
                },
            },
        },
    }
    msg_type = message_router.classify_message(msg)
    assert msg_type is None


def test_classify_message_group_info_wrong_type(message_router):
    """Test classify_message handles non-UPDATE group info."""
    msg = {
        "envelope": {
            "dataMessage": {
                "groupInfo": {
                    "type": "DELIVER",
                    "groupId": "internal-123",
                },
            },
        },
    }
    msg_type = message_router.classify_message(msg)
    assert msg_type is None


# Test route_message


@pytest.mark.asyncio
async def test_route_message_received_message(
    message_router, mock_hass, received_message_data
):
    """Test route_message routes received message correctly."""
    await message_router.route_message(received_message_data)

    # Verify event was fired
    mock_hass.bus.async_fire.assert_called_once_with(
        EVENT_SIGNAL_RECEIVED, received_message_data
    )


@pytest.mark.asyncio
async def test_route_message_group_update(
    message_router,
    mock_hass,
    mock_entry,
    mock_signal_client,
    group_update_message_data,
    sample_group,
):
    """Test route_message routes group update by refreshing the group coordinator."""
    # Setup coordinator for the updated group
    sample_group.internal_id = "internal-group-id-123"
    mock_coordinator = MagicMock(spec=SignalGroupCoordinator)
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators={"group_internal-group-id-123": mock_coordinator},
    )

    await message_router.route_message(group_update_message_data)

    # API not called; coordinator is refreshed directly
    mock_signal_client.list_groups.assert_not_called()
    mock_coordinator.async_request_refresh.assert_called_once()

    # No additional events fired
    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_route_message_typing_indicator(
    message_router, mock_hass, typing_indicator_data
):
    """Test route_message routes typing indicator correctly."""
    await message_router.route_message(typing_indicator_data)

    # Verify typing indicator event was fired
    mock_hass.bus.async_fire.assert_called_once()
    call_args = mock_hass.bus.async_fire.call_args
    assert call_args[0][0] == f"{DOMAIN}_{EVENT_TYPING_INDICATOR}"
    event_data = call_args[0][1]
    assert event_data["entry_id"] == "test_entry_123"
    assert event_data["source"] == "+1234567890"
    assert event_data["source_uuid"] == "test-uuid"
    assert event_data["action"] == "started"
    assert event_data["timestamp"] == 1234567890000


@pytest.mark.asyncio
async def test_route_message_unrecognized(
    message_router, mock_hass, unrecognized_message_data
):
    """Test route_message handles unrecognized messages gracefully."""
    await message_router.route_message(unrecognized_message_data)

    # No events should be fired for unrecognized messages
    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_route_message_handler_error(message_router, mock_hass):
    """Test route_message propagates handler errors (no exception suppression)."""
    # Create a message that will be classified but cause an error in the handler
    msg = {
        "envelope": {
            "dataMessage": {
                "message": "test",
            },
        },
    }

    # Make async_fire raise an exception
    mock_hass.bus.async_fire.side_effect = Exception("Event bus error")

    # Exception propagates from the handler
    with pytest.raises(Exception, match="Event bus error"):
        await message_router.route_message(msg)

    # Event bus was called (before raising)
    mock_hass.bus.async_fire.assert_called_once()


# Test _handle_received_message


@pytest.mark.asyncio
async def test_handle_received_message(
    message_router, mock_hass, received_message_data
):
    """Test _handle_received_message fires the correct event."""
    await message_router._handle_received_message(received_message_data)

    mock_hass.bus.async_fire.assert_called_once_with(
        EVENT_SIGNAL_RECEIVED, received_message_data
    )


# Test _handle_group_update


@pytest.mark.asyncio
async def test_handle_group_update_success(
    message_router, mock_hass, mock_entry, mock_signal_client, sample_group
):
    """Test _handle_group_update refreshes the coordinator for the updated group."""
    msg = {
        "envelope": {
            "dataMessage": {
                "groupInfo": {
                    "groupId": "internal-abc",
                    "revision": 10,
                    "type": "UPDATE",
                },
            },
        },
    }

    sample_group.internal_id = "internal-abc"
    mock_coordinator = MagicMock(spec=SignalGroupCoordinator)
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators={"group_internal-abc": mock_coordinator},
    )

    await message_router._handle_group_update(msg)

    # API not called; coordinator refreshed directly
    mock_signal_client.list_groups.assert_not_called()
    mock_coordinator.async_request_refresh.assert_called_once()

    # No event fired
    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_handle_group_update_group_not_found(
    message_router, mock_hass, mock_signal_client, sample_group
):
    """Test _handle_group_update when no coordinator exists for the group."""
    msg = {
        "envelope": {
            "dataMessage": {
                "groupInfo": {
                    "groupId": "nonexistent-internal-id",
                    "revision": 5,
                    "type": "UPDATE",
                },
            },
        },
    }

    # No coordinator registered for this group ID (fixture uses empty coordinators)
    await message_router._handle_group_update(msg)

    # API not called
    mock_signal_client.list_groups.assert_not_called()

    # No event fired when coordinator not found
    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_handle_group_update_coordinator_refresh_error(
    message_router, mock_hass, mock_entry, mock_signal_client
):
    """Test _handle_group_update when coordinator refresh raises an exception."""
    msg = {
        "envelope": {
            "dataMessage": {
                "groupInfo": {
                    "groupId": "internal-123",
                    "revision": 5,
                    "type": "UPDATE",
                },
            },
        },
    }

    mock_coordinator = MagicMock(spec=SignalGroupCoordinator)
    mock_coordinator.async_request_refresh = AsyncMock(
        side_effect=Exception("Refresh failed")
    )
    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators={"group_internal-123": mock_coordinator},
    )

    # Exception from coordinator.async_request_refresh propagates
    with pytest.raises(Exception, match="Refresh failed"):
        await message_router._handle_group_update(msg)

    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_handle_group_update_no_coordinator(
    message_router, mock_hass, mock_signal_client
):
    """Test _handle_group_update when no coordinator is registered for the group."""
    msg = {
        "envelope": {
            "dataMessage": {
                "groupInfo": {
                    "groupId": "internal-123",
                    "revision": 5,
                    "type": "UPDATE",
                },
            },
        },
    }

    # Fixture uses empty coordinators — no coordinator for "group_internal-123"
    await message_router._handle_group_update(msg)

    # No event should be fired
    mock_hass.bus.async_fire.assert_not_called()


# Test _handle_typing_indicator


@pytest.mark.asyncio
async def test_handle_typing_indicator_contact(
    message_router, mock_hass, typing_indicator_data
):
    """Test _handle_typing_indicator handles contact typing indicators."""
    await message_router._handle_typing_indicator(typing_indicator_data)

    # Verify event was fired
    mock_hass.bus.async_fire.assert_called_once()
    call_args = mock_hass.bus.async_fire.call_args
    assert call_args[0][0] == f"{DOMAIN}_{EVENT_TYPING_INDICATOR}"
    event_data = call_args[0][1]
    assert event_data["entry_id"] == "test_entry_123"
    assert event_data["source"] == "+1234567890"
    assert event_data["source_uuid"] == "test-uuid"
    assert event_data["action"] == "started"


@pytest.mark.asyncio
async def test_handle_typing_indicator_stopped(
    message_router, mock_hass, typing_indicator_data
):
    """Test _handle_typing_indicator handles STOPPED action."""
    # Modify the action to STOPPED
    typing_indicator_data["envelope"]["typingMessage"]["action"] = "STOPPED"

    await message_router._handle_typing_indicator(typing_indicator_data)

    # Verify event was fired with correct action
    mock_hass.bus.async_fire.assert_called_once()
    call_args = mock_hass.bus.async_fire.call_args
    event_data = call_args[0][1]
    assert event_data["action"] == "stopped"


@pytest.mark.asyncio
async def test_handle_typing_indicator_group_ignored(
    message_router, mock_hass, group_typing_indicator_data
):
    """Test _handle_typing_indicator ignores group typing indicators."""
    await message_router._handle_typing_indicator(group_typing_indicator_data)

    # No event should be fired for group typing indicators
    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_handle_typing_indicator_missing_source(message_router, mock_hass):
    """Test _handle_typing_indicator handles missing source gracefully."""
    msg = {
        "envelope": {
            "typingMessage": {
                "action": "STARTED",
                "timestamp": 1234567890000,
            },
        },
    }

    await message_router._handle_typing_indicator(msg)

    # No event should be fired when source is missing
    mock_hass.bus.async_fire.assert_not_called()


# Integration tests


@pytest.mark.asyncio
async def test_router_initialization(mock_hass, mock_entry, mock_signal_client):
    """Test SignalMessageRouter initialization."""
    router = SignalMessageRouter(
        hass=mock_hass,
        entry=mock_entry,
        client=mock_signal_client,
    )

    assert router._hass == mock_hass
    assert router._entry == mock_entry
    assert router._client == mock_signal_client
    assert "received_message" in router._handlers
    assert "group_update" in router._handlers
    assert "typing_indicator" in router._handlers


@pytest.mark.asyncio
async def test_multiple_messages_in_sequence(
    message_router, mock_hass, mock_entry, received_message_data, mock_signal_client, sample_group
):
    """Test handling multiple messages in sequence."""
    # First message: received message
    await message_router.route_message(received_message_data)

    # Verify received message event fired
    assert mock_hass.bus.async_fire.call_count == 1
    first_call = mock_hass.bus.async_fire.call_args_list[0]
    assert first_call[0][0] == EVENT_SIGNAL_RECEIVED

    # Second message: group update — setup coordinator
    sample_group.internal_id = "internal-123"
    mock_coordinator = MagicMock(spec=SignalGroupCoordinator)
    mock_coordinator.async_request_refresh = AsyncMock()
    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators={"group_internal-123": mock_coordinator},
    )

    group_update = {
        "envelope": {
            "dataMessage": {
                "groupInfo": {
                    "type": "UPDATE",
                    "groupId": "internal-123",
                    "revision": 5,
                },
            },
        },
    }
    await message_router.route_message(group_update)

    # Only the received-message event was fired; group update uses coordinator refresh
    assert mock_hass.bus.async_fire.call_count == 1
    mock_coordinator.async_request_refresh.assert_called_once()
