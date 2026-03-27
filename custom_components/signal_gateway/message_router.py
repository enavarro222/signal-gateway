"""Signal message router for classifying and handling incoming messages."""

from __future__ import annotations

import logging
from typing import Callable, Awaitable, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, EVENT_SIGNAL_RECEIVED
from .signal import SignalClient

_LOGGER = logging.getLogger(__name__)


class SignalMessageRouter:
    """Routes incoming Signal messages to appropriate handlers based on message type."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SignalClient,
    ) -> None:
        """Initialize the message router.

        Args:
            hass: Home Assistant instance
            entry: Config entry for this integration
            client: Signal API client instance
        """
        self._hass = hass
        self._entry = entry
        self._client = client
        self._handlers: Dict[str, Callable[[dict], Awaitable[None]]] = {
            "received_message": self._handle_received_message,
            "group_update": self._handle_group_update,
            # Future: "typing_indicator": self._handle_typing_indicator,
            # Future: "reaction": self._handle_reaction,
        }

    def classify_message(self, msg: dict) -> Optional[str]:
        """Classify the incoming message type.

        Args:
            msg: The raw message data from the websocket

        Returns:
            str: Message type identifier or None if unrecognized
        """
        envelope = msg.get("envelope", {})
        data_message = envelope.get("dataMessage", {})
        group_info = data_message.get("groupInfo", {})

        # Check for group update notification
        if group_info.get("type") == "UPDATE" and group_info.get("groupId"):
            return "group_update"

        # Check for regular received message (with text content)
        if data_message and data_message.get("message") is not None:
            return "received_message"

        # Future: Add typing indicator detection
        # if "typingMessage" in envelope:
        #     return "typing_indicator"

        # Future: Add reaction detection
        # if data_message.get("reaction"):
        #     return "reaction"

        return None

    async def route_message(self, msg: dict) -> None:
        """Route message to appropriate handler.

        Args:
            msg: The raw message data from the websocket
        """
        try:
            # Classify and route to specific handler
            msg_type = self.classify_message(msg)
            if msg_type and msg_type in self._handlers:
                await self._handlers[msg_type](msg)
            elif msg_type:
                _LOGGER.debug("No handler registered for message type: %s", msg_type)
            else:
                _LOGGER.debug("Unrecognized message type, skipping routing")

        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error routing Signal message: %s", err)

    async def _handle_received_message(self, msg: dict) -> None:
        """Handle a regular received message with text content.

        Args:
            msg: The message data
        """
        # Fire the signal received event for received messages
        self._hass.bus.async_fire(EVENT_SIGNAL_RECEIVED, msg)

    async def _handle_group_update(self, msg: dict) -> None:
        """Handle a group update notification.

        This occurs when group name, permissions, members, or other metadata changes.

        Args:
            msg: The message data containing group update information
        """
        envelope = msg.get("envelope", {})
        data_message = envelope.get("dataMessage", {})
        group_info = data_message.get("groupInfo", {})

        internal_id = group_info.get("groupId")
        _LOGGER.info(
            "Group with internal_id %s updated, refreshing data (revision %s)",
            internal_id,
            group_info.get("revision"),
        )

        # Fetch all groups and find the one with matching internal_id
        # groupId from websocket is actually the internal_id, not the API id
        try:
            groups = await self._client.list_groups()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error fetching group data from API: %s", err)
            return

        updated_group = next((g for g in groups if g.internal_id == internal_id), None)
        if not updated_group:
            _LOGGER.warning(
                "Could not find group with internal_id %s in API response",
                internal_id,
            )
            return
        # Future: add a method on the client to fetch a single group by internal_id
        # the client may cache a mapping of internal_id -> id for efficiency

        # Fire event to update all related entities
        self._hass.bus.async_fire(
            f"{DOMAIN}_group_updated",
            {
                "entry_id": self._entry.entry_id,
                "group": updated_group,
            },
        )
        _LOGGER.debug(
            "Fired group update event for %s (internal_id: %s)",
            updated_group.name,
            internal_id,
        )

    async def _handle_typing_indicator(
        self, msg: dict
    ) -> None:  # pylint: disable=unused-argument
        """Handle a typing indicator notification.

        This occurs when a user starts or stops typing.

        Args:
            msg: The message data containing typing information
        """
        # Future implementation for typing indicators
        # Will fire events that binary_sensor entities can listen to
        _LOGGER.debug("Typing indicator received: %s", msg)
