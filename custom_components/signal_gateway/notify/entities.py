"""Notify entities for Signal Gateway - per-device (contact/group) notification entities.

Note: Home Assistant's NotifyEntity framework currently only supports text messages
(message + optional title). Attachments must be sent via the legacy notify service:
    service: notify.signal_gateway
    data:
      message: "Hello"
      attachments: ["/path/to/file.jpg"]

For more details see: https://developers.home-assistant.io/docs/core/entity/notify/
"""

from __future__ import annotations

import logging

from homeassistant.components.notify import NotifyEntity

from ..device import SignalContactBaseEntity, SignalGroupBaseEntity
from .helpers import prepare_message
from ..coordinator import SignalContactCoordinator, SignalGroupCoordinator

_LOGGER = logging.getLogger(__name__)


class SignalContactNotifyEntity(SignalContactBaseEntity, NotifyEntity):
    """Notify entity for sending messages to a Signal contact."""

    _attr_icon = "mdi:message-text"

    def __init__(self, coordinator: SignalContactCoordinator) -> None:
        """Initialize the Signal contact notify entity."""
        super().__init__(coordinator)
        self._attr_name = "Notify"
        # Note: changed from contact.number to contact.uuid for consistency
        # with sensor/binary_sensor/text platforms (breaking change from previous versions)
        self._attr_unique_id = (
            f"{coordinator.entry_id}_contact_{coordinator.data.uuid}_notify"
        )

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        """Send a message to this contact."""
        full_message = prepare_message(message, title)
        try:
            await self.coordinator.client.send_message(
                target=self.contact.number,
                message=full_message,
                base64_attachments=[],
            )
            _LOGGER.info("Sent message to %s", self.contact.display_name)
        except Exception as err:
            _LOGGER.error(
                "Failed to send message to %s: %s",
                self.contact.display_name,
                err,
            )
            raise


class SignalGroupNotifyEntity(SignalGroupBaseEntity, NotifyEntity):
    """Notify entity for sending messages to a Signal group."""

    _attr_icon = "mdi:message-text"

    def __init__(self, coordinator: SignalGroupCoordinator) -> None:
        """Initialize the Signal group notify entity."""
        super().__init__(coordinator)
        self._attr_name = "Notify"
        self._attr_unique_id = (
            f"{coordinator.entry_id}_group_{coordinator.data.id}_notify"
        )

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        """Send a message to this group."""
        full_message = prepare_message(message, title)
        try:
            await self.coordinator.client.send_message(
                target=self.group.id,
                message=full_message,
                base64_attachments=[],
            )
            _LOGGER.info("Sent message to %s", self.group.name)
        except Exception as err:
            _LOGGER.error(
                "Failed to send message to %s: %s",
                self.group.name,
                err,
            )
            raise
