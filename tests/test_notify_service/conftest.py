"""Shared fixtures for notify service tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.signal_gateway.notify import SignalGatewayNotificationService


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_register = MagicMock()
    return hass


@pytest.fixture
def mock_signal_client():
    """Create a mock Signal client."""
    client = AsyncMock()
    client.send_message = AsyncMock(return_value={"success": True})
    return client


@pytest.fixture
def notification_service(mock_hass, mock_signal_client):
    """Create a notification service instance."""
    return SignalGatewayNotificationService(
        hass=mock_hass,
        client=mock_signal_client,
        default_recipients=["+1234567890"],
    )
