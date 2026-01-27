"""Unified Signal client combining HTTP and WebSocket capabilities."""

from __future__ import annotations

from typing import Any, Callable, Optional

import aiohttp

from .http_client import SignalHTTPClient
from .websocket_listener import SignalWebSocketListener

_LOGGER = None  # Will be initialized if needed


class SignalClient:
    """Unified client for Signal-cli-rest-api with HTTP and WebSocket support."""

    def __init__(self, api_url: str, phone_number: str, session: aiohttp.ClientSession):
        """Initialize the Signal client.

        Args:
            api_url: Base URL of the Signal-cli-rest-api service
            phone_number: Phone number associated with this Signal account
            session: aiohttp ClientSession for HTTP requests
        """
        self._http_client = SignalHTTPClient(api_url, phone_number, session)
        self._ws_listener = SignalWebSocketListener(api_url, phone_number, session)

    async def send_message(
        self,
        target: str,
        message: str,
        attachments: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Send a message via Signal.

        Args:
            target: Phone number or group ID to send to
            message: Message text to send
            attachments: Optional list of attachment URLs

        Returns:
            Response from the API
        """
        return await self._http_client.send_message(target, message, attachments)

    def set_message_handler(self, handler: Callable[[dict[str, Any]], Any]) -> None:
        """Set the callback handler for incoming WebSocket messages.

        Args:
            handler: Async callable that receives message dictionaries
        """
        self._ws_listener.set_message_handler(handler)

    async def start_listening(self) -> None:
        """Connect to the WebSocket and start listening for incoming messages."""
        await self._ws_listener.connect()

    async def stop_listening(self) -> None:
        """Disconnect from the WebSocket."""
        await self._ws_listener.disconnect()
