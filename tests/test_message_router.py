"""Tests for SignalMessageRouter."""

# pylint: disable=redefined-outer-name,protected-access

import pytest

from custom_components.signal_gateway.message_router import SignalMessageRouter
from custom_components.signal_gateway.const import DOMAIN, EVENT_SIGNAL_RECEIVED


@pytest.fixture
def message_router(mock_hass, mock_entry, mock_signal_client):
    """Create a SignalMessageRouter instance."""
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
    """Sample typing indicator data (future feature)."""
    return {
        "envelope": {
            "source": "+1234567890",
            "sourceNumber": "+1234567890",
            "sourceUuid": "test-uuid",
            "timestamp": 1234567890000,
            "typingMessage": {
                "action": "STARTED",
                "timestamp": 1234567890000,
                "groupId": None,
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
    mock_signal_client,
    group_update_message_data,
    sample_group,
):
    """Test route_message routes group update correctly."""
    # Setup mock client to return the updated group
    sample_group.internal_id = "internal-group-id-123"
    mock_signal_client.list_groups.return_value = [sample_group]

    await message_router.route_message(group_update_message_data)

    # Verify groups were fetched
    mock_signal_client.list_groups.assert_called_once()

    # Verify group_updated event was fired
    assert mock_hass.bus.async_fire.call_count == 1
    call_args = mock_hass.bus.async_fire.call_args
    assert call_args[0][0] == f"{DOMAIN}_group_updated"
    assert call_args[0][1]["entry_id"] == "test_entry_123"
    assert call_args[0][1]["group"] == sample_group


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
    """Test route_message handles handler errors gracefully."""
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

    # Should not raise exception
    await message_router.route_message(msg)

    # Event bus should have been called
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
    message_router, mock_hass, mock_signal_client, sample_group
):
    """Test _handle_group_update successfully updates group data."""
    # Setup message data
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

    # Setup mock client to return the updated group
    sample_group.internal_id = "internal-abc"
    mock_signal_client.list_groups.return_value = [sample_group]

    await message_router._handle_group_update(msg)

    # Verify groups were fetched
    mock_signal_client.list_groups.assert_called_once()

    # Verify event was fired with correct data
    mock_hass.bus.async_fire.assert_called_once()
    call_args = mock_hass.bus.async_fire.call_args
    assert call_args[0][0] == f"{DOMAIN}_group_updated"
    assert call_args[0][1]["entry_id"] == "test_entry_123"
    assert call_args[0][1]["group"] == sample_group


@pytest.mark.asyncio
async def test_handle_group_update_group_not_found(
    message_router, mock_hass, mock_signal_client, sample_group
):
    """Test _handle_group_update when group is not found in API response."""
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

    # Return a group with different internal_id
    sample_group.internal_id = "different-id"
    mock_signal_client.list_groups.return_value = [sample_group]

    await message_router._handle_group_update(msg)

    # Verify groups were fetched
    mock_signal_client.list_groups.assert_called_once()

    # No event should be fired when group is not found
    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_handle_group_update_api_error(
    message_router, mock_hass, mock_signal_client
):
    """Test _handle_group_update handles API errors gracefully."""
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

    # Make API call raise an exception
    mock_signal_client.list_groups.side_effect = Exception("API connection failed")

    await message_router._handle_group_update(msg)

    # Verify API was called
    mock_signal_client.list_groups.assert_called_once()

    # No event should be fired when API fails
    mock_hass.bus.async_fire.assert_not_called()


@pytest.mark.asyncio
async def test_handle_group_update_empty_groups_list(
    message_router, mock_hass, mock_signal_client
):
    """Test _handle_group_update when API returns empty groups list."""
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

    # Return empty list
    mock_signal_client.list_groups.return_value = []

    await message_router._handle_group_update(msg)

    # No event should be fired
    mock_hass.bus.async_fire.assert_not_called()


# Test _handle_typing_indicator (future feature)


@pytest.mark.asyncio
async def test_handle_typing_indicator_placeholder(
    message_router, typing_indicator_data
):
    """Test _handle_typing_indicator placeholder implementation."""
    # This is a placeholder test for the future typing indicator feature
    # Currently just verifies the method doesn't raise errors
    await message_router._handle_typing_indicator(typing_indicator_data)
    # No assertions - just verify it doesn't crash


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


@pytest.mark.asyncio
async def test_multiple_messages_in_sequence(
    message_router, mock_hass, received_message_data, mock_signal_client, sample_group
):
    """Test handling multiple messages in sequence."""
    # First message: received message
    await message_router.route_message(received_message_data)

    # Second message: group update
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
    sample_group.internal_id = "internal-123"
    mock_signal_client.list_groups.return_value = [sample_group]

    await message_router.route_message(group_update)

    # Verify both events were fired
    assert mock_hass.bus.async_fire.call_count == 2

    # Check first call was for received message
    first_call = mock_hass.bus.async_fire.call_args_list[0]
    assert first_call[0][0] == EVENT_SIGNAL_RECEIVED

    # Check second call was for group update
    second_call = mock_hass.bus.async_fire.call_args_list[1]
    assert second_call[0][0] == f"{DOMAIN}_group_updated"
