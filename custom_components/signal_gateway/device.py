"""Common device and entity base classes for Signal contacts and groups."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .signal import SignalClient
from .signal.models import SignalContact, SignalGroup

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant


class SignalDeviceEntity(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for entities that belong to a Signal contact or group device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        client: SignalClient,
        entry_id: str,
    ) -> None:
        """Initialize the Signal device entity."""
        self._client = client
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information to link entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._get_device_identifier())},
            name=self._get_device_name(),
            manufacturer="Signal Messenger",
            model=self._get_device_model(),
        )

    @abstractmethod
    def _get_device_identifier(self) -> str:
        """Get the unique device identifier."""

    @abstractmethod
    def _get_device_name(self) -> str:
        """Get the device display name."""

    @abstractmethod
    def _get_device_model(self) -> str:
        """Get the device model (Contact or Group)."""


class ContactDeviceMixin(SignalDeviceEntity):  # pylint: disable=too-few-public-methods
    """Mixin for entities representing a Signal contact device."""

    def __init__(
        self, contact: SignalContact, client: SignalClient, entry_id: str, **kwargs
    ) -> None:
        """Initialize contact device mixin."""
        super().__init__(client=client, entry_id=entry_id)
        self._contact = contact
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _get_device_identifier(self) -> str:
        """Get the unique device identifier for this contact."""
        return f"{self._entry_id}_contact_{self._contact.number}"

    def _get_device_name(self) -> str:
        """Get the device display name for this contact."""
        return self._contact.display_name

    def _get_device_model(self) -> str:
        """Get the device model."""
        return "Contact"


class GroupDeviceMixin(SignalDeviceEntity):  # pylint: disable=too-few-public-methods
    """Mixin for entities representing a Signal group device."""

    if TYPE_CHECKING:
        hass: HomeAssistant
        async_on_remove: Callable[[Callable[[], None]], None]

    def __init__(
        self, group: SignalGroup, client: SignalClient, entry_id: str, **kwargs
    ) -> None:
        """Initialize group device mixin."""
        super().__init__(client=client, entry_id=entry_id)
        self._group = group
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _get_device_identifier(self) -> str:
        """Get the unique device identifier for this group."""
        return f"{self._entry_id}_group_{self._group.id}"

    def _get_device_name(self) -> str:
        """Get the device display name for this group."""
        return self._group.name

    def _get_device_model(self) -> str:
        """Get the device model."""
        return "Group"

    async def async_added_to_hass(self) -> None:
        """Register event listener when entity is added to hass."""
        # Call super if it exists (Entity class provides this method)
        if hasattr(super(), "async_added_to_hass"):
            await super().async_added_to_hass()  # type: ignore[misc]

        # Listen for group update events
        unsubscribe = self.hass.bus.async_listen(
            f"{DOMAIN}_group_updated",
            self._handle_group_updated,
        )
        self.async_on_remove(unsubscribe)

    async def _handle_group_updated(self, event) -> None:
        """Handle group updated event."""
        data = event.data
        updated_group = data.get("group")
        if (
            data.get("entry_id") == self._entry_id
            and updated_group
            and updated_group.id == self._group.id
        ):
            # Replace the entire group object with fresh data
            self._update_group(updated_group, write_state=True)

    @abstractmethod
    def _update_group(self, group: SignalGroup, write_state: bool = False) -> None:
        """Update the group and native value.

        Must be implemented by subclasses to handle group-specific updates.

        Args:
            group: The updated group object
            write_state: Whether to write the state to Home Assistant
        """

    def _update_device_name(self) -> None:
        """Update the device name in the device registry.

        This should be called when the group name changes to keep the
        device registry in sync. Only updates if user hasn't set a custom name.
        """
        # Check if hass is available (entity is registered)
        if not hasattr(self, "hass") or self.hass is None:
            return

        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, self._get_device_identifier())}
        )

        if device_entry and device_entry.name_by_user is None:
            # Only update if user hasn't set a custom name
            device_registry.async_update_device(
                device_entry.id,
                name=self._group.name,
            )
