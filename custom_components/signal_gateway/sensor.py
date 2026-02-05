"""Sensor platform for Signal Gateway - displays contact and group information."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_APPROVED_DEVICES, DOMAIN
from .device import ContactDeviceMixin, GroupDeviceMixin
from .signal import SignalClient
from .signal.models import SignalContact, SignalGroup

from .avatar_view import generate_avatar_token

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Signal Gateway sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: SignalClient = data["client"]

    # Get approved devices from config
    approved_devices = entry.data.get(CONF_APPROVED_DEVICES)

    entities: list[SensorEntity] = []

    # Fetch contacts and groups from Signal API
    # If this fails, let the exception propagate - HA will retry the setup
    contacts = await client.list_contacts()
    _LOGGER.debug("Fetched %d contacts for sensor platform", len(contacts))

    for contact in contacts:
        # Only add entity if:
        # - No approval list was configured (backward compatibility), OR
        # - Device is in the approved list
        device_id = f"contact_{contact.number}"
        if approved_devices is None or device_id in approved_devices:
            entities.append(SignalContactInfoEntity(client, contact, entry.entry_id))

    # Fetch groups from the Signal API
    groups = await client.list_groups()
    _LOGGER.debug("Fetched %d groups for sensor platform", len(groups))

    for group in groups:
        # Only add entity if:
        # - No approval list was configured (backward compatibility), OR
        # - Device is in the approved list
        device_id = f"group_{group.id}"
        if approved_devices is None or device_id in approved_devices:
            entities.append(SignalGroupInfoEntity(client, group, entry.entry_id))

    _LOGGER.info("Setting up %d Signal sensor entities", len(entities))
    async_add_entities(entities, True)


class SignalContactInfoEntity(ContactDeviceMixin, SensorEntity):
    """Sensor entity displaying Signal contact information."""

    _attr_icon = "mdi:account-details"

    def __init__(
        self,
        client: SignalClient,
        contact: SignalContact,
        entry_id: str,
    ) -> None:
        """Initialize the Signal contact info entity."""
        super().__init__(contact=contact, entry_id=entry_id, client=client)
        self._attr_name = "Info"
        self._attr_unique_id = f"{entry_id}_contact_{contact.number}_info"
        self._attr_native_value = contact.display_name

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use for this contact."""
        if self._contact.profile and self._contact.profile.has_avatar:
            token, _ = generate_avatar_token(
                self.hass, self._entry_id, self._contact.uuid
            )
            return (
                f"/api/signal_gateway/{self._entry_id}/avatar/contact/"
                f"{self._contact.uuid}?token={token}"
            )
        return None

    async def async_added_to_hass(self) -> None:
        """Register event listener when entity is added to hass."""
        await super().async_added_to_hass()
        # Listen for contact update events
        unsubscribe = self.hass.bus.async_listen(
            f"{DOMAIN}_contact_updated",
            self._handle_contact_updated,
        )
        self.async_on_remove(unsubscribe)

    async def _handle_contact_updated(self, event) -> None:
        """Handle contact updated event."""
        data = event.data
        if (
            data.get("entry_id") == self._entry_id
            and data.get("contact_number") == self._contact.number
        ):
            # Update with the entire contact object
            updated_contact = data.get("contact")
            if updated_contact:
                self._contact = updated_contact
                self._attr_native_value = self._contact.display_name
                self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            "number": self._contact.number,
            "uuid": self._contact.uuid,
            "type": "contact",
        }

        # Avatar information
        if self._contact.profile:
            attrs["has_avatar"] = self._contact.profile.has_avatar
            if self._contact.profile.has_avatar:
                attrs["avatar_url"] = self.entity_picture

        if self._contact.name:
            attrs["name"] = self._contact.name
        if self._contact.given_name:
            attrs["given_name"] = self._contact.given_name
        if self._contact.profile_name:
            attrs["profile_name"] = self._contact.profile_name
        if self._contact.username:
            attrs["username"] = self._contact.username
        if self._contact.nickname:
            if self._contact.nickname.given_name:
                attrs["nickname"] = self._contact.nickname.given_name
            if self._contact.nickname.family_name:
                attrs["nickname_family"] = self._contact.nickname.family_name
        if self._contact.blocked:
            attrs["blocked"] = bool(self._contact.blocked)
        if self._contact.color:
            attrs["color"] = self._contact.color
        if self._contact.message_expiration and self._contact.message_expiration != "0":
            attrs["message_expiration"] = self._contact.message_expiration

        return attrs


class SignalGroupInfoEntity(GroupDeviceMixin, SensorEntity):
    """Sensor entity displaying Signal group information."""

    _attr_icon = "mdi:account-group-outline"

    def __init__(
        self,
        client: SignalClient,
        group: SignalGroup,
        entry_id: str,
    ) -> None:
        """Initialize the Signal group info entity."""
        super().__init__(group=group, entry_id=entry_id, client=client)
        self._attr_name = "Info"
        self._attr_unique_id = f"{entry_id}_group_{group.id}_info"
        self._update_group(group)

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use for this group.

        Groups always have avatars, so always return the URL.
        If the avatar doesn't exist, the view will return 404.
        """
        token, _ = generate_avatar_token(self.hass, self._entry_id, self._group.id)
        return (
            f"/api/signal_gateway/{self._entry_id}/avatar/group/"
            f"{self._group.id}?token={token}"
        )

    def _update_group(self, group: SignalGroup, write_state: bool = False) -> None:
        """Update the group and native value.

        Args:
            group: The updated group object
            write_state: Whether to write the state to Home Assistant
        """
        self._group = group
        self._attr_native_value = group.name
        if write_state:
            # Update device name in registry (sensor is the primary entity for device updates)
            self._update_device_name()
            self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "group_id": self._group.id,
            "internal_id": self._group.internal_id,
            "type": "group",
            "member_count": self._group.member_count,
            "members": self._group.members,
            "admins": self._group.admins,
        }

        # Avatar information (groups always have avatars)
        attrs["avatar_url"] = self.entity_picture

        if self._group.description:
            attrs["description"] = self._group.description
        if self._group.invite_link:
            attrs["invite_link"] = self._group.invite_link
        if self._group.blocked:
            attrs["blocked"] = self._group.blocked
        if self._group.pending_invites:
            attrs["pending_invites"] = self._group.pending_invites
        if self._group.pending_requests:
            attrs["pending_requests"] = self._group.pending_requests
        if self._group.permissions:
            attrs["permissions"] = {
                "add_members": self._group.permissions.add_members,
                "edit_group": self._group.permissions.edit_group,
                "send_messages": self._group.permissions.send_messages,
            }
        if self._group.is_admin_only:
            attrs["is_admin_only"] = self._group.is_admin_only

        return attrs
