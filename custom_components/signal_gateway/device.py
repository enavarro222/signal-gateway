"""Base entity classes for Signal contacts and groups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SignalContactCoordinator, SignalGroupCoordinator
from .device_helpers import build_group_device_identifier
from .signal.models import SignalContact, SignalGroup

if TYPE_CHECKING:
    pass


class SignalContactBaseEntity(CoordinatorEntity[SignalContactCoordinator]):
    """Abstract base for all Signal contact entities.

    Provides coordinator-backed contact data and device_info. Subclasses
    only need to set unique_id and implement their platform-specific logic.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: SignalContactCoordinator) -> None:
        """Initialize the Signal contact base entity."""
        super().__init__(coordinator)

    @property
    def contact(self) -> SignalContact:
        """Return the current contact data from the coordinator."""
        return self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo | None:
        """Delegate device info to the coordinator."""
        return self.coordinator.device_info


class SignalGroupBaseEntity(CoordinatorEntity[SignalGroupCoordinator]):
    """Abstract base for all Signal group entities.

    Provides coordinator-backed group data and device_info. Registers a
    listener for group_updated bus events to keep the device registry in sync
    when a group is renamed via websocket or the text entity.
    """

    _attr_has_entity_name = True

    def __init__(self, coordinator: SignalGroupCoordinator) -> None:
        """Initialize the Signal group base entity."""
        super().__init__(coordinator)

    @property
    def group(self) -> SignalGroup:
        """Return the current group data from the coordinator."""
        return self.coordinator.data

    @property
    def device_info(self) -> DeviceInfo | None:
        """Delegate device info to the coordinator."""
        return self.coordinator.device_info
