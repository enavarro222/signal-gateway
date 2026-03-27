"""Sensor platform for Signal Gateway - displays contact and group information."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import event as event_helpers
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_APPROVED_DEVICES, DOMAIN
from .device import SignalContactBaseEntity, SignalGroupBaseEntity
from .coordinator import SignalContactCoordinator, SignalGroupCoordinator
from .avatar_view import generate_avatar_token

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Signal Gateway sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client = data["client"]
    coordinators: dict[str, SignalContactCoordinator | SignalGroupCoordinator] = data[
        "coordinators"
    ]
    approved_devices = entry.data.get(CONF_APPROVED_DEVICES)

    entities: list[SensorEntity] = []

    contacts = await client.list_contacts()
    _LOGGER.debug("Fetched %d contacts for sensor platform", len(contacts))

    for contact in contacts:
        device_id = f"contact_{contact.number}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = coordinators.get(f"contact_{contact.uuid}")
            if coordinator:
                entities.append(SignalContactInfoEntity(coordinator))

    groups = await client.list_groups()
    _LOGGER.debug("Fetched %d groups for sensor platform", len(groups))

    for group in groups:
        device_id = f"group_{group.id}"
        if approved_devices is None or device_id in approved_devices:
            coordinator = coordinators.get(f"group_{group.id}")
            if coordinator:
                entities.append(SignalGroupInfoEntity(coordinator))

    _LOGGER.info("Setting up %d Signal sensor entities", len(entities))
    async_add_entities(entities, True)


class SignalContactInfoEntity(SignalContactBaseEntity, SensorEntity):
    """Sensor entity displaying Signal contact information."""

    _attr_icon = "mdi:account-details"

    def __init__(self, coordinator: SignalContactCoordinator) -> None:
        """Initialize the Signal contact info entity."""
        super().__init__(coordinator)
        self._attr_name = "Info"
        self._attr_unique_id = f"{coordinator.entry_id}_contact_{coordinator.data.uuid}_info"
        self._attr_native_value = coordinator.data.display_name

    @property
    def native_value(self) -> str | None:
        """Return the contact display name as state."""
        return self.contact.display_name if self.contact else None

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture URL for this contact."""
        contact = self.contact
        if self.hass is not None and contact and contact.profile and contact.profile.has_avatar:
            token, _ = generate_avatar_token(
                self.hass, self.coordinator.entry_id, contact.uuid
            )
            return (
                f"/api/signal_gateway/{self.coordinator.entry_id}/avatar/contact/"
                f"{contact.uuid}?token={token}"
            )
        return None

    async def async_added_to_hass(self) -> None:
        """Register periodic refresh when entity is added to hass."""
        await super().async_added_to_hass()

        # Refresh state every 30 minutes to update avatar tokens before they expire (1h)
        async def _async_refresh_token(_now):
            self.async_write_ha_state()

        self.async_on_remove(
            event_helpers.async_track_time_interval(
                self.hass,
                _async_refresh_token,
                timedelta(minutes=30),
            )
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        contact = self.contact
        if not contact:
            return {}

        attrs: dict[str, Any] = {
            "number": contact.number,
            "uuid": contact.uuid,
            "type": "contact",
        }

        if contact.profile:
            attrs["has_avatar"] = contact.profile.has_avatar
            if contact.profile.has_avatar:
                attrs["avatar_url"] = self.entity_picture

        if contact.name:
            attrs["name"] = contact.name
        if contact.given_name:
            attrs["given_name"] = contact.given_name
        if contact.profile_name:
            attrs["profile_name"] = contact.profile_name
        if contact.username:
            attrs["username"] = contact.username
        if contact.nickname:
            if contact.nickname.given_name:
                attrs["nickname"] = contact.nickname.given_name
            if contact.nickname.family_name:
                attrs["nickname_family"] = contact.nickname.family_name
        if contact.blocked:
            attrs["blocked"] = bool(contact.blocked)
        if contact.color:
            attrs["color"] = contact.color
        if contact.message_expiration and contact.message_expiration != "0":
            attrs["message_expiration"] = contact.message_expiration

        return attrs


class SignalGroupInfoEntity(SignalGroupBaseEntity, SensorEntity):
    """Sensor entity displaying Signal group information."""

    _attr_icon = "mdi:account-group-outline"

    def __init__(self, coordinator: SignalGroupCoordinator) -> None:
        """Initialize the Signal group info entity."""
        super().__init__(coordinator)
        self._attr_name = "Info"
        self._attr_unique_id = f"{coordinator.entry_id}_group_{coordinator.data.id}_info"
        self._attr_native_value = coordinator.data.name

    @property
    def native_value(self) -> str | None:
        """Return the group name as state."""
        return self.group.name if self.group else None

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture URL for this group.

        Groups always have avatars; a 404 from the view means no avatar is set.
        """
        if self.hass is None or not self.group:
            return None
        token, _ = generate_avatar_token(
            self.hass, self.coordinator.entry_id, self.group.id
        )
        return (
            f"/api/signal_gateway/{self.coordinator.entry_id}/avatar/group/"
            f"{self.group.id}?token={token}"
        )

    async def async_added_to_hass(self) -> None:
        """Register periodic refresh when entity is added to hass."""
        await super().async_added_to_hass()  # registers group_updated listener

        # Refresh state every 30 minutes to update avatar tokens before they expire (1h)
        async def _async_refresh_token(_now):
            self.async_write_ha_state()

        self.async_on_remove(
            event_helpers.async_track_time_interval(
                self.hass,
                _async_refresh_token,
                timedelta(minutes=30),
            )
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        group = self.group
        if not group:
            return {}

        attrs: dict[str, Any] = {
            "group_id": group.id,
            "internal_id": group.internal_id,
            "type": "group",
            "member_count": group.member_count,
            "members": group.members,
            "admins": group.admins,
            "avatar_url": self.entity_picture,
        }

        if group.description:
            attrs["description"] = group.description
        if group.invite_link:
            attrs["invite_link"] = group.invite_link
        if group.blocked:
            attrs["blocked"] = group.blocked
        if group.pending_invites:
            attrs["pending_invites"] = group.pending_invites
        if group.pending_requests:
            attrs["pending_requests"] = group.pending_requests
        if group.permissions:
            attrs["permissions"] = {
                "add_members": group.permissions.add_members,
                "edit_group": group.permissions.edit_group,
                "send_messages": group.permissions.send_messages,
            }
        if group.is_admin_only:
            attrs["is_admin_only"] = group.is_admin_only

        return attrs
