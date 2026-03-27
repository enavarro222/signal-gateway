"""Unified Signal client combining HTTP and WebSocket capabilities."""

from __future__ import annotations

from typing import Any, Callable

import aiohttp

from .http_client import SignalHTTPClient
from .websocket_listener import SignalWebSocketListener

_LOGGER = None  # Will be initialized if needed


class SignalClient(SignalHTTPClient):
    """Unified client for Signal-cli-rest-api with HTTP and WebSocket support.

    Inherits all HTTP methods from SignalHTTPClient and adds WebSocket functionality.
    """

    def __init__(self, api_url: str, phone_number: str, session: aiohttp.ClientSession):
        """Initialize the Signal client.

        Args:
            api_url: Base URL of the Signal-cli-rest-api service
            phone_number: Phone number associated with this Signal account
            session: aiohttp ClientSession for HTTP requests
        """
        super().__init__(api_url, phone_number, session)
        self._ws_listener = SignalWebSocketListener(api_url, phone_number, session)

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
