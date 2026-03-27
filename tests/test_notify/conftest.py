"""Shared fixtures for notify service tests."""

import pytest

from custom_components.signal_gateway.notify.service import (
    SignalGatewayNotificationService,
)
from custom_components.signal_gateway.notify.attachments import AttachmentProcessor


@pytest.fixture
def notification_service(mock_hass, mock_signal_client):
    """Create a notification service instance."""
    return SignalGatewayNotificationService(
        hass=mock_hass,
        client=mock_signal_client,
        default_recipients=["+1234567890"],
    )


@pytest.fixture
def attachment_processor(mock_hass):
    """Create an attachment processor instance."""
    return AttachmentProcessor(mock_hass)
