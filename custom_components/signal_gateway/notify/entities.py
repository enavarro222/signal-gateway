"""Notify entities for Signal Gateway - per-device (ie contact/group) notification entities.

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
from abc import abstractmethod

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from ..device import ContactDeviceMixin, GroupDeviceMixin
from .helpers import prepare_message
from ..signal import SignalClient
from ..signal.models import SignalContact, SignalGroup

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Signal Gateway notify entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: SignalClient = data["client"]

    entities: list[NotifyEntity] = []

    try:
        # Fetch contacts from the Signal API
        contacts = await client.list_contacts()
        _LOGGER.debug("Fetched %d contacts for notify platform", len(contacts))

        for contact in contacts:
            entities.append(SignalContactNotifyEntity(client, contact, entry.entry_id))

        # Fetch groups from the Signal API
        groups = await client.list_groups()
        _LOGGER.debug("Fetched %d groups for notify platform", len(groups))

        for group in groups:
            entities.append(SignalGroupNotifyEntity(client, group, entry.entry_id))

    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Failed to fetch contacts/groups for notify platform: %s", err)

    _LOGGER.info("Setting up %d Signal notify entities", len(entities))
    async_add_entities(entities, True)


class SignalNotifyEntity(NotifyEntity):
    """Base class for Signal notify entities."""

    _attr_icon = "mdi:message-text"

    def __init__(self, client: SignalClient) -> None:
        """Initialize the base notify entity."""
        self._client = client

    @property
    @abstractmethod
    def _target(self) -> str:
        """Return the target (phone number or group ID)."""

    @property
    @abstractmethod
    def _display_name(self) -> str:
        """Return the display name for logging."""

    async def async_send_message(
        self,
        message: str,
        title: str | None = None,
    ) -> None:
        """Send a message to this target.

        Args:
            message: The message text to send
            title: Optional title to prepend to the message

        Note:
            Attachments are not supported by Home Assistant's NotifyEntity framework.
            Use the legacy notify service for attachment support.
        """
        full_message = prepare_message(message, title)

        try:
            await self._client.send_message(  # pylint: disable=no-member
                target=self._target,
                message=full_message,
                base64_attachments=[],
            )
            _LOGGER.info("Sent message to %s", self._display_name)
        except Exception as err:
            _LOGGER.error(
                "Failed to send message to %s: %s",
                self._display_name,
                err,
            )
            raise


class SignalContactNotifyEntity(ContactDeviceMixin, SignalNotifyEntity):
    """Notify entity for sending messages to a Signal contact."""

    def __init__(
        self,
        client: SignalClient,
        contact: SignalContact,
        entry_id: str,
    ) -> None:
        """Initialize the Signal contact notify entity."""
        ContactDeviceMixin.__init__(
            self, contact=contact, entry_id=entry_id, client=client
        )
        SignalNotifyEntity.__init__(self, client=client)
        self._attr_name = "Notify"
        self._attr_unique_id = f"{entry_id}_contact_{contact.number}_notify"

    @property
    def _target(self) -> str:
        """Return the contact's phone number."""
        return self._contact.number

    @property
    def _display_name(self) -> str:
        """Return the contact's display name."""
        return self._contact.display_name


class SignalGroupNotifyEntity(GroupDeviceMixin, SignalNotifyEntity):
    """Notify entity for sending messages to a Signal group."""

    def __init__(
        self,
        client: SignalClient,
        group: SignalGroup,
        entry_id: str,
    ) -> None:
        """Initialize the Signal group notify entity."""
        GroupDeviceMixin.__init__(self, group=group, entry_id=entry_id, client=client)
        SignalNotifyEntity.__init__(self, client=client)
        self._attr_name = "Notify"
        self._attr_unique_id = f"{entry_id}_group_{group.id}_notify"

    @property
    def _target(self) -> str:
        """Return the group ID."""
        return self._group.id

    @property
    def _display_name(self) -> str:
        """Return the group name."""
        return self._group.name

    def _update_group(self, group: SignalGroup, write_state: bool = False) -> None:
        """Update the group object.

        Args:
            group: The updated group object
            write_state: Whether to write the state to Home Assistant
        """
        self._group = group
        if write_state:
            self.async_write_ha_state()
