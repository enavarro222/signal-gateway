"""Coordinator for Signal Gateway devices (contacts and groups)."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.helpers import device_registry as dr
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo

from .signal import SignalClient
from .signal.models import SignalContact, SignalGroup
from .device_helpers import (
    build_contact_device_identifier,
    build_group_device_identifier,
    build_group_internal_identifier,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class SignalContactCoordinator(DataUpdateCoordinator[SignalContact]):
    """Coordinator for a single Signal contact.

    Owns both the contact data (via DataUpdateCoordinator) and the
    device_info used by all contact entities on this device.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: SignalClient,
        entry_id: str,
        contact_uuid: str,
        update_interval: timedelta | None = None,
    ) -> None:
        """Initialize the contact coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Signal contact_{contact_uuid}",
            update_interval=update_interval or timedelta(minutes=30),
        )
        self.client = client
        self.entry_id = entry_id
        self.contact_uuid = contact_uuid

    async def _async_update_data(self) -> SignalContact:
        """Fetch contact data from Signal API."""
        try:
            return await self.client.get_contact(self.contact_uuid)
        except Exception as err:
            _LOGGER.error("Error fetching contact %s: %s", self.contact_uuid, err)
            raise

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for this contact.

        Computed from live coordinator data — always in sync without caching.
        """
        if self.data is None:
            return None
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    build_contact_device_identifier(self.entry_id, self.data.number),
                )
            },
            name=self.data.display_name,
            manufacturer="Signal Messenger",
            model="Contact",
        )

    def invalidate_device_info(self) -> None:
        """No-op: device_info is computed directly from self.data, no cache to clear."""


class SignalGroupCoordinator(DataUpdateCoordinator[SignalGroup]):
    """Coordinator for a single Signal group.

    Owns both the group data (via DataUpdateCoordinator) and the
    device_info used by all group entities on this device.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: SignalClient,
        entry_id: str,
        group_id: str,
        update_interval: timedelta | None = None,
    ) -> None:
        """Initialize the group coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Signal group_{group_id}",
            update_interval=update_interval or timedelta(minutes=15),
        )
        self.client = client
        self.entry_id = entry_id
        self.group_id = group_id
        self.async_add_listener(self._update_device_name)

    async def _async_update_data(self) -> SignalGroup:
        """Fetch group data from Signal API."""
        try:
            return await self.client.get_group(self.group_id)
        except Exception as err:
            _LOGGER.error("Error fetching group %s: %s", self.group_id, err)
            raise

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for this group.

        Includes both the API id and internal_id as identifiers so
        websocket messages (which use internal_id) can match this device.
        """
        if self.data is None:
            return None
        return DeviceInfo(
            identifiers={
                (DOMAIN, build_group_device_identifier(self.entry_id, self.data.id)),
                (
                    DOMAIN,
                    build_group_internal_identifier(
                        self.entry_id, self.data.internal_id
                    ),
                ),
            },
            name=self.data.name,
            manufacturer="Signal Messenger",
            model="Group",
        )

    def invalidate_device_info(self) -> None:
        """No-op: device_info is computed directly from self.data, no cache to clear."""

    def _update_device_name(self) -> None:
        """Update device registry name when a group is renamed.

        Only updates if the user has not set a custom name for this device.
        """
        if self.data is None:
            return
        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(
            identifiers={
                (
                    DOMAIN,
                    build_group_device_identifier(self.entry_id, self.data.id),
                )
            }
        )
        if device_entry and device_entry.name_by_user is None:
            _LOGGER.debug("Update device group, new name: %s", self.data.name)
            device_registry.async_update_device(
                device_entry.id,
                name=self.data.name,
            )
