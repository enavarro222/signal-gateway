"""WebSocket listener for Signal messages."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class SignalWebSocketListener:
    """Listen for incoming Signal messages via WebSocket."""

    max_retries: int = (
        10  # Maximum number of connection retry attempts before giving up
    )
    retry_delay: int = 5  # Delay (in seconds) between connection retry attempts

    def __init__(
        self, api_url: str, phone_number: str, session: aiohttp.ClientSession
    ) -> None:
        """Initialize the WebSocket listener."""
        self.api_url = api_url.rstrip("/")
        self.phone_number = phone_number
        self.session = session
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

        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=5)
            except asyncio.TimeoutError:
                _LOGGER.warning("WebSocket listener task did not complete in time")
                self._task.cancel()
            except asyncio.CancelledError:
                pass

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
        """Connect to WebSocket and listen for messages."""
        async with self.session.ws_connect(
            ws_url, timeout=aiohttp.ClientTimeout(total=None)
        ) as websocket:
            _LOGGER.info("Connected to Signal WebSocket")
            try:
                async for msg in websocket:
                    if not self._running:
                        break
                    if not await self._process_ws_message(msg, websocket):
                        break
            except asyncio.CancelledError:
                _LOGGER.info("WebSocket listening task cancelled")
            except Exception as err:
                _LOGGER.error("Error processing WebSocket messages: %s", err)
                raise

    async def _process_ws_message(
        self, msg: aiohttp.WSMessage, websocket: aiohttp.ClientWebSocketResponse
    ) -> bool:
        """Process a single message from the WebSocket connection.

        Returns:
            bool: True to continue listening, False to stop.
        """
        if msg.type == aiohttp.WSMsgType.TEXT:
            await self._handle_message(msg.data)
            return True
        elif msg.type == aiohttp.WSMsgType.ERROR:
            _LOGGER.error("WebSocket error: %s", websocket.exception())
            return False
        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
            _LOGGER.info("WebSocket connection closed")
            return False
        return True

    async def _handle_message(self, message: str) -> None:
        try:
            data = json.loads(message)
            if self._message_handler:
                await self._message_handler(data)
        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to parse WebSocket message: %s", err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error handling WebSocket message: %s", err)
