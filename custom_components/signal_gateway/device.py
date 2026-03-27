"""Common device and entity base classes for Signal contacts and groups."""

from __future__ import annotations

from abc import ABC, abstractmethod

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .signal import SignalClient
from .signal.models import SignalContact, SignalGroup


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
