"""Text platform for Signal Gateway - editable contact and group names."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_APPROVED_DEVICES, DOMAIN
from .device import ContactDeviceMixin, GroupDeviceMixin
from .signal import SignalClient
from .signal.models import SignalContact, SignalGroup

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Signal Gateway text entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: SignalClient = data["client"]

    # Get approved devices from config
    approved_devices = entry.data.get(CONF_APPROVED_DEVICES)

    entities: list[TextEntity] = []

    # Fetch contacts and groups from Signal API
    contacts = await client.list_contacts()
    _LOGGER.debug("Fetched %d contacts for text platform", len(contacts))

    for contact in contacts:
        device_id = f"contact_{contact.number}"
        if approved_devices is None or device_id in approved_devices:
            entities.append(SignalContactNameEntity(client, contact, entry.entry_id))

    # Fetch groups from the Signal API
    groups = await client.list_groups()
    _LOGGER.debug("Fetched %d groups for text platform", len(groups))

    for group in groups:
        device_id = f"group_{group.id}"
        if approved_devices is None or device_id in approved_devices:
            entities.append(SignalGroupNameEntity(client, group, entry.entry_id))

    _LOGGER.info("Setting up %d Signal text entities", len(entities))
    async_add_entities(entities, True)


class SignalContactNameEntity(ContactDeviceMixin, TextEntity):
    """Text entity for editing Signal contact name."""

    _attr_icon = "mdi:account-edit"
    _attr_native_max = 255
    _attr_native_min = 0

    def __init__(
        self,
        client: SignalClient,
        contact: SignalContact,
        entry_id: str,
    ) -> None:
        """Initialize the Signal contact name entity."""
        super().__init__(contact=contact, entry_id=entry_id, client=client)
        self._attr_name = "Name"
        self._attr_unique_id = f"{entry_id}_contact_{contact.number}_name"
        self._attr_native_value = contact.display_name or contact.number

    async def async_set_value(self, value: str) -> None:
        """Update the contact name in Signal."""
        try:
            await self._client.update_contact(
                recipient=self._contact.number, name=value
            )
            # Update internal state
            self._contact.name = value
            self._attr_native_value = value
            self.async_write_ha_state()

            # Refresh related sensor entity
            await self._refresh_related_entities()

            _LOGGER.info("Updated contact %s name to '%s'", self._contact.number, value)
        except Exception as err:
            _LOGGER.error(
                "Failed to update contact %s name: %s", self._contact.number, err
            )
            raise

    async def _refresh_related_entities(self) -> None:
        """Refresh sensor and other entities for this contact."""
        # Fire an event to signal that the contact data has changed
        # Other entities listening for this can refresh themselves
        self.hass.bus.async_fire(
            f"{DOMAIN}_contact_updated",
            {
                "entry_id": self._entry_id,
                "contact": self._contact,
            },
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "number": self._contact.number,
            "uuid": self._contact.uuid,
            "type": "contact",
        }


class SignalGroupNameEntity(GroupDeviceMixin, TextEntity):
    """Text entity for editing Signal group name."""

    _attr_icon = "mdi:account-group-outline"
    _attr_native_max = 255
    _attr_native_min = 0

    def __init__(
        self,
        client: SignalClient,
        group: SignalGroup,
        entry_id: str,
    ) -> None:
        """Initialize the Signal group name entity."""
        super().__init__(group=group, entry_id=entry_id, client=client)
        self._attr_name = "Name"
        self._attr_unique_id = f"{entry_id}_group_{group.id}_name"
        self._update_group(group)

    def _update_group(self, group: SignalGroup, write_state: bool = False) -> None:
        """Update the group and native value.

        Args:
            group: The updated group object
            write_state: Whether to write the state to Home Assistant
        """
        self._group = group
        self._attr_native_value = group.name or group.id

        if write_state:
            # Write state (this forces re-evaluation of available property)
            # Note: Device name update is handled by sensor entity (primary)
            self.async_write_ha_state()

    async def async_set_value(self, value: str) -> None:
        """Update the group name in Signal."""
        try:
            await self._client.update_group(group_id=self._group.id, name=value)
            _LOGGER.info("Updated group %s name to '%s'", self._group.id, value)
        except Exception as err:
            _LOGGER.error("Failed to update group %s name: %s", self._group.id, err)
            raise

        await self._resync_from_api()

    async def _resync_from_api(self) -> None:
        """Reload the group and notify changes ."""
        # Fire an event to signal that the group data (may) has changed
        # Other entities (and ourself) listening for this can refresh themselves
        #
        # Note: we reload the group from API to ensure change has been validated
        # there is no way to check if we have permission to update the group name
        # until we try, so we need to refresh the group data from the server.
        updated_group = await self._client.get_group(self._group.id)
        # Refresh related sensor entity
        self.hass.bus.async_fire(
            f"{DOMAIN}_group_updated",
            {
                "entry_id": self._entry_id,
                "group": updated_group,
            },
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "group_id": self._group.id,
            "internal_id": self._group.internal_id,
            "type": "group",
        }
