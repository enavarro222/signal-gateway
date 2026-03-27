"""Text platform for Signal Gateway - editable contact and group names."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_APPROVED_DEVICES, DOMAIN
from .device import SignalContactBaseEntity, SignalGroupBaseEntity
from .coordinator import SignalContactCoordinator, SignalGroupCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Signal Gateway text entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    coordinators = data["coordinators"]
    approved_devices = entry.data.get(CONF_APPROVED_DEVICES)

    entities: list[TextEntity] = []

    contacts = await client.list_contacts()
    _LOGGER.debug("Fetched %d contacts for text platform", len(contacts))

    for contact in contacts:
        device_id = f"contact_{contact.number}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = coordinators.get(f"contact_{contact.uuid}")
            if coordinator:
                entities.append(SignalContactNameEntity(coordinator))

    groups = await client.list_groups()
    _LOGGER.debug("Fetched %d groups for text platform", len(groups))

    for group in groups:
        device_id = f"group_{group.id}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = coordinators.get(f"group_{group.id}")
            if coordinator:
                entities.append(SignalGroupNameEntity(coordinator))

    _LOGGER.info("Setting up %d Signal text entities", len(entities))
    async_add_entities(entities, True)


class SignalContactNameEntity(SignalContactBaseEntity, TextEntity):
    """Text entity for editing Signal contact name."""

    _attr_icon = "mdi:account-edit"
    _attr_native_max = 255
    _attr_native_min = 0

    def __init__(self, coordinator: SignalContactCoordinator) -> None:
        """Initialize the Signal contact name entity."""
        super().__init__(coordinator)
        self._attr_name = "Name"
        self._attr_unique_id = (
            f"{coordinator.entry_id}_contact_{coordinator.data.uuid}_name"
        )
        self._attr_native_value = coordinator.data.display_name

    @property
    def native_value(self) -> str | None:
        """Return the contact display name."""
        return self.contact.display_name if self.contact else None

    async def async_set_value(self, value: str) -> None:
        """Update the contact name in Signal."""
        try:
            await self.coordinator.client.update_contact(
                recipient=self.contact.number, name=value
            )
            # Coordinator refresh propagates the new name to all entities on this device
            await self.coordinator.async_request_refresh()
            self.async_write_ha_state()
            _LOGGER.info("Updated contact %s name to '%s'", self.contact.number, value)
        except Exception as err:
            _LOGGER.error(
                "Failed to update contact %s name: %s", self.contact.number, err
            )
            raise

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.contact:
            return {}
        return {
            "number": self.contact.number,
            "uuid": self.contact.uuid,
            "type": "contact",
        }


class SignalGroupNameEntity(SignalGroupBaseEntity, TextEntity):
    """Text entity for editing Signal group name."""

    _attr_icon = "mdi:account-group-outline"
    _attr_native_max = 255
    _attr_native_min = 0

    def __init__(self, coordinator: SignalGroupCoordinator) -> None:
        """Initialize the Signal group name entity."""
        super().__init__(coordinator)
        self._attr_name = "Name"
        self._attr_unique_id = (
            f"{coordinator.entry_id}_group_{coordinator.data.id}_name"
        )
        self._attr_native_value = coordinator.data.name or coordinator.data.id

    @property
    def native_value(self) -> str | None:
        """Return the group name."""
        if not self.group:
            return None
        return self.group.name or self.group.id

    async def async_set_value(self, value: str) -> None:
        """Update the group name in Signal."""
        try:
            await self.coordinator.client.update_group(
                group_id=self.coordinator.group_id, name=value
            )
            _LOGGER.info("Updated group %s name to '%s'", self.coordinator.group_id, value)
        except Exception as err:
            _LOGGER.error(
                "Failed to update group %s name: %s", self.coordinator.group_id, err
            )
            raise

        # Fetch the updated group from API and notify all sibling entities via
        # the group_updated bus event (also triggers coordinator refresh in SignalGroupBaseEntity)
        await self._resync_from_api()

    async def _resync_from_api(self) -> None:
        """Reload the group from API and fire group_updated for all sibling entities."""
        updated_group = await self.coordinator.client.get_group(self.coordinator.group_id)
        self.hass.bus.async_fire(
            f"{DOMAIN}_group_updated",
            {
                "entry_id": self.coordinator.entry_id,
                "group": updated_group,
            },
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.group:
            return {}
        return {
            "group_id": self.group.id,
            "internal_id": self.group.internal_id,
            "type": "group",
        }
