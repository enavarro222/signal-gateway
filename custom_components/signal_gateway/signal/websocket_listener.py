"""WebSocket listener for Signal messages."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

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
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Error while disconnecting WebSocket: %s", err)
            finally:
                self._task = None

    async def _listen(self) -> None:
        """Listen for messages from the WebSocket."""
        ws_url = f"{self.api_url.replace('http', 'ws')}/v1/receive/{self.phone_number}"
        retry_count = 0

        try:
            while self._running:
                try:
                    await self._connect_and_listen(ws_url)
                    retry_count = 0  # Reset retry count on successful connection
                except asyncio.CancelledError:
                    # Task was cancelled, exit cleanly
                    _LOGGER.info("WebSocket listener task cancelled")
                    raise
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
                        try:
                            await asyncio.sleep(self.retry_delay)
                        except asyncio.CancelledError:
                            _LOGGER.info(
                                "WebSocket listener task cancelled during retry delay"
                            )
                            raise
                    else:
                        break
        finally:
            _LOGGER.info("WebSocket listener stopped")

    async def _connect_and_listen(self, ws_url: str) -> None:
        """Connect to WebSocket and listen for messages."""
        # Use ws_close=None to avoid timeout on connection close
        timeout = aiohttp.ClientWSTimeout(ws_close=None)
        async with self.session.ws_connect(ws_url, timeout=timeout) as websocket:
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
        if msg.type == aiohttp.WSMsgType.ERROR:
            _LOGGER.error("WebSocket error: %s", websocket.exception())
            return False
        if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
            _LOGGER.info("WebSocket connection closed")
            return False
        return True

    def is_received_msg(self, msg: Dict) -> bool:
        """Check if the message is a 'receive' type message."""
        envelope = msg.get("envelope", {})
        return (
            envelope.get("dataMessage") is not None
            and envelope["dataMessage"].get("message") is not None
        )

    async def _handle_message(self, message: str) -> None:
        try:
            data = json.loads(message)
            _LOGGER.debug("Received WebSocket data: %s", data)
            if self._message_handler and self.is_received_msg(data):
                await self._message_handler(data)
        except json.JSONDecodeError as err:
            _LOGGER.error("Failed to parse WebSocket message: %s", err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error handling WebSocket message: %s", err)
