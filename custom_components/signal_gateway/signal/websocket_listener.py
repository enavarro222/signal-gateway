"""WebSocket listener for Signal messages."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import websockets
from websockets.client import ClientConnection

_LOGGER = logging.getLogger(__name__)


class SignalWebSocketListener:
    """Listen for incoming Signal messages via WebSocket."""

    max_retries: int = (
        10  # Maximum number of connection retry attempts before giving up
    )
    retry_delay: int = 5  # Delay (in seconds) between connection retry attempts

    def __init__(self, api_url: str, phone_number: str):
        """Initialize the WebSocket listener."""
        self.api_url = api_url.rstrip("/")
        self.phone_number = phone_number
        self.websocket: Optional[ClientConnection] = None
        self._task: Optional[asyncio.Task[None]] = None
        self._message_handler: Optional[Callable[[dict[str, Any]], Any]] = None
        self._running = False

    def set_message_handler(self, handler: Callable[[dict[str, Any]], Any]) -> None:
        """Set the callback handler for incoming messages."""
        self._message_handler = handler

    async def connect(self) -> None:
        """Connect to the WebSocket and start listening."""
        if self._running:
            _LOGGER.warning("WebSocket listener is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._listen())

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket."""
        self._running = False

        if self.websocket:
            await self.websocket.close()

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                _LOGGER.warning("WebSocket listener task did not complete in time")
                self._task.cancel()

    async def _listen(self) -> None:
        """Listen for messages from the WebSocket."""
        ws_url = f"{self.api_url.replace('http', 'ws')}/v1/receive/{self.phone_number}"
        retry_count = 0

        while self._running:
            try:
                await self._connect_and_listen(ws_url)
                retry_count = 0  # Reset retry count on successful connection
            except Exception as err:  # pylint: disable=broad-except
                if self._running:
                    retry_count += 1
                    if retry_count > self.max_retries:
                        _LOGGER.error(
                            "Failed to connect to Signal WebSocket after %d retries: %s",
                            self.max_retries,
                            err,
                        )
                        self._running = False
                        break

                    _LOGGER.warning(
                        "Failed to connect to Signal WebSocket (attempt %d/%d): %s. "
                        "Retrying in %d seconds...",
                        retry_count,
                        self.max_retries,
                        err,
                        self.retry_delay,
                    )
                    await asyncio.sleep(self.retry_delay)
                else:
                    break

        _LOGGER.info("WebSocket listener stopped")

    async def _connect_and_listen(self, ws_url: str) -> None:
        async with websockets.connect(
            ws_url,
            close_timeout=5,
        ) as websocket:
            assert websocket is not None
            self.websocket = websocket
            _LOGGER.info("Connected to Signal WebSocket")
            try:
                async for message in websocket:
                    if not self._running:
                        break
                    await self._handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                _LOGGER.info("WebSocket connection closed")
            except asyncio.CancelledError:  # listening task is cancelled by main code
                _LOGGER.debug("WebSocket listening task cancelled")
                pass

    async def _handle_message(self, message: str) -> None:
        try:
            data = json.loads(message)
            if self._message_handler:
                await self._message_handler(data)
        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to parse WebSocket message: %s", err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error handling WebSocket message: %s", err)
