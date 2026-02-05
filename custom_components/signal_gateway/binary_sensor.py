"""Binary sensor platform for Signal Gateway - tracks typing indicators."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up Signal Gateway binary sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: SignalClient = data["client"]

    # Get approved devices from config
    approved_devices = entry.data.get(CONF_APPROVED_DEVICES)

    entities: list[BinarySensorEntity] = []

    # Fetch contacts and groups from Signal API
    # If this fails, let the exception propagate - HA will retry the setup
    contacts = await client.list_contacts()
    _LOGGER.debug("Fetched %d contacts for binary_sensor platform", len(contacts))

    for contact in contacts:
        # Only add entity if:
        # - No approval list was configured (backward compatibility), OR
        # - Device is in the approved list
        device_id = f"contact_{contact.number}"
        if approved_devices is None or device_id in approved_devices:
            entities.append(
                SignalContactIsWritingEntity(client, contact, entry.entry_id)
            )

    # Fetch groups from the Signal API
    groups = await client.list_groups()
    _LOGGER.debug("Fetched %d groups for binary_sensor platform", len(groups))

    for group in groups:
        # Only add entity if:
        # - No approval list was configured (backward compatibility), OR
        # - Device is in the approved list
        device_id = f"group_{group.id}"
        if approved_devices is None or device_id in approved_devices:
            entities.append(SignalGroupIsWritingEntity(client, group, entry.entry_id))

    _LOGGER.info("Setting up %d Signal binary sensor entities", len(entities))
    async_add_entities(entities, True)


class SignalContactIsWritingEntity(ContactDeviceMixin, BinarySensorEntity):
    """Binary sensor showing if a contact is writing."""

    _attr_icon = "mdi:pencil"

    def __init__(
        self,
        client: SignalClient,
        contact: SignalContact,
        entry_id: str,
    ) -> None:
        """Initialize the Signal contact is_writing entity."""
        super().__init__(contact=contact, entry_id=entry_id, client=client)
        self._attr_name = "Is Writing"
        self._attr_unique_id = f"{entry_id}_contact_{contact.number}_is_writing"
        self._attr_is_on = False  # Default to not writing


class SignalGroupIsWritingEntity(GroupDeviceMixin, BinarySensorEntity):
    """Binary sensor showing if someone in a group is writing."""

    _attr_icon = "mdi:pencil"

    def __init__(
        self,
        client: SignalClient,
        group: SignalGroup,
        entry_id: str,
    ) -> None:
        """Initialize the Signal group is_writing entity."""
        super().__init__(group=group, entry_id=entry_id, client=client)
        self._attr_name = "Is Writing"
        self._attr_unique_id = f"{entry_id}_group_{group.id}_is_writing"
        self._attr_is_on = False  # Default to not writing

    def _update_group(self, group: SignalGroup, write_state: bool = False) -> None:
        """Update the group object.

        Args:
            group: The updated group object
            write_state: Whether to write the state to Home Assistant
        """
        self._group = group
        if write_state:
            self.async_write_ha_state()
