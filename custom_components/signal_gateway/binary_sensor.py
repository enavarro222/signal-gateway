"""Binary sensor platform for Signal Gateway - tracks typing indicators."""

from __future__ import annotations

from typing import Callable
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, CONF_APPROVED_DEVICES, EVENT_TYPING_INDICATOR
from .device import SignalContactBaseEntity, SignalGroupBaseEntity
from .coordinator import SignalContactCoordinator, SignalGroupCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Signal Gateway binary sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client = data.client
    approved_devices = entry.data.get(CONF_APPROVED_DEVICES)

    entities: list[BinarySensorEntity] = []

    contacts = await client.list_contacts()
    _LOGGER.debug("Fetched %d contacts for binary_sensor platform", len(contacts))

    for contact in contacts:
        device_id = f"contact_{contact.number}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = data.get_contact_coordinator(contact)
            if coordinator:
                entities.append(SignalContactIsWritingEntity(coordinator))

    groups = await client.list_groups()
    _LOGGER.debug("Fetched %d groups for binary_sensor platform", len(groups))

    for group in groups:
        device_id = f"group_{group.id}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = data.get_group_coordinator(group)
            if coordinator:
                entities.append(SignalGroupIsWritingEntity(coordinator))

    _LOGGER.info("Setting up %d Signal binary sensor entities", len(entities))
    async_add_entities(entities, True)


class SignalContactIsWritingEntity(SignalContactBaseEntity, BinarySensorEntity):
    """Binary sensor showing if a contact is currently typing."""

    _attr_icon = "mdi:pencil"
    _typing_timeout_seconds = 10  # Auto-reset to False after this many seconds

    def __init__(self, coordinator: SignalContactCoordinator) -> None:
        """Initialize the Signal contact is_writing entity."""
        super().__init__(coordinator)
        self._attr_name = "Is Writing"
        self._attr_unique_id = (
            f"{coordinator.entry_id}_contact_{coordinator.data.uuid}_is_writing"
        )
        self._attr_is_on = False
        self._reset_timer: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Subscribe to typing indicator events when added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.hass.bus.async_listen(
                f"{DOMAIN}_{EVENT_TYPING_INDICATOR}",
                self._handle_typing_event,
            )
        )
        _LOGGER.debug(
            "Contact %s subscribed to typing indicator events",
            self.contact.number,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Cancel pending reset timer when removed from hass."""
        await super().async_will_remove_from_hass()
        if self._reset_timer:
            self._reset_timer()
            self._reset_timer = None

    @callback
    def _handle_typing_event(self, event: Event) -> None:
        """Handle typing indicator event for this contact."""
        event_data = event.data

        if (
            event_data.get("entry_id") != self.coordinator.entry_id
            or event_data.get("source") != self.contact.number
        ):
            return

        action = event_data.get("action", "")
        _LOGGER.debug("Contact %s typing indicator: %s", self.contact.number, action)

        if action == "started":
            self._attr_is_on = True
            self.async_write_ha_state()

            if self._reset_timer:
                self._reset_timer()

            self._reset_timer = async_call_later(
                self.hass,
                self._typing_timeout_seconds,
                self._reset_typing_state,
            )

        elif action == "stopped":
            self._attr_is_on = False
            self.async_write_ha_state()

            if self._reset_timer:
                self._reset_timer()
                self._reset_timer = None

    @callback
    def _reset_typing_state(self, _now) -> None:
        """Reset typing state after the auto-reset timeout."""
        _LOGGER.debug(
            "Contact %s typing indicator timed out, resetting state",
            self.contact.number,
        )
        self._attr_is_on = False
        self._reset_timer = None
        self.async_write_ha_state()


class SignalGroupIsWritingEntity(SignalGroupBaseEntity, BinarySensorEntity):
    """Binary sensor showing if someone in a group is typing.

    Note: Signal's group typing indicators are not currently routed by the
    message_router, so this sensor always remains False.
    """

    _attr_icon = "mdi:pencil"

    def __init__(self, coordinator: SignalGroupCoordinator) -> None:
        """Initialize the Signal group is_writing entity."""
        super().__init__(coordinator)
        self._attr_name = "Is Writing"
        self._attr_unique_id = (
            f"{coordinator.entry_id}_group_{coordinator.data.id}_is_writing"
        )
        self._attr_is_on = False
