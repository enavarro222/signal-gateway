"""Data structures for Signal Gateway entry data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .coordinator import SignalContactCoordinator, SignalGroupCoordinator

if TYPE_CHECKING:
    from .signal import SignalClient
    from .signal.models import SignalContact, SignalGroup

@dataclass
class SignalGatewayEntryData:
    """Typed container stored per config entry in hass.data[DOMAIN][entry_id]."""

    client: SignalClient
    service_name: str
    default_recipients: list[str]
    coordinators: dict[str, SignalContactCoordinator | SignalGroupCoordinator] = field(
        default_factory=dict
    )

    def get_contact_coordinator(
        self, contact: SignalContact
    ) -> SignalContactCoordinator | None:
        """Return the coordinator for the given contact, or None."""
        return self.coordinators.get(f"contact_{contact.uuid}")  # type: ignore[return-value]

    def get_group_coordinator(
        self, group: SignalGroup
    ) -> SignalGroupCoordinator | None:
        """Return the coordinator for the given group, or None."""
        return self.coordinators.get(f"group_{group.internal_id}")  # type: ignore[return-value]
