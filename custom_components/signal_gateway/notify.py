"""Notification service for Signal Gateway."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any, Optional, Union

import aiohttp
import voluptuous as vol

from homeassistant.components.notify import (
    BaseNotificationService,
    DOMAIN as NOTIFY_DOMAIN,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service import async_set_service_schema

from .const import DOMAIN
from .signal import SignalClient

_LOGGER = logging.getLogger(__name__)

SERVICE_SEND_MESSAGE = "send_message"

# Attachment constraints
CONF_MAX_ALLOWED_DOWNLOAD_SIZE_BYTES = 52428800  # 50 MB
ATTR_FILENAMES = "attachments"
ATTR_URLS = "urls"
ATTR_VERIFY_SSL = "verify_ssl"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,  # pylint: disable=unused-argument
) -> bool:
    """Set up Signal Gateway notify from a config entry."""
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        _LOGGER.error("Signal Gateway client not found for entry %s", entry.entry_id)
        return False

    client = hass.data[DOMAIN][entry.entry_id].get("client")
    if not client:
        _LOGGER.error("Signal Gateway client not initialized")
        return False

    # Get default recipients from config
    default_recipients = hass.data[DOMAIN][entry.entry_id].get("default_recipients", [])

    # Create the notification service
    service = SignalGatewayNotificationService(hass, client, default_recipients)

    # Register the Home Assistant service
    async def handle_send_message(call):
        """Handle send message service call."""
        _LOGGER.debug(
            "Sending message to target=%s, message starts with: %s",
            call.data.get("target"),
            call.data.get("message", "")[:50],
        )
        await service.async_send_message(
            message=call.data.get("message"),
            title=call.data.get("title"),
            target=call.data.get("target"),
            attachments=call.data.get("attachments"),
            urls=call.data.get("urls"),
            verify_ssl=call.data.get("verify_ssl", True),
            text_mode=call.data.get("text_mode", "normal"),
        )

    # Get the service name from the config entry
    service_name = hass.data[DOMAIN][entry.entry_id]["service_name"]

    _LOGGER.debug(
        "Registering Signal Gateway notify service '%s' for entry %s",
        service_name,
        entry.entry_id,
    )
    hass.services.async_register(
        NOTIFY_DOMAIN,
        service_name,
        handle_send_message,
        schema=vol.Schema(
            {
                vol.Required("message"): cv.string,
                vol.Optional("title"): cv.string,
                vol.Optional("target"): vol.Any(cv.string, [cv.string]),
                vol.Optional("attachments"): [cv.string],
                vol.Optional("urls"): [cv.string],
                vol.Optional("verify_ssl"): cv.boolean,
                vol.Optional("text_mode"): vol.In(["normal", "styled"]),
            }
        ),
    )

    # Set service schema for GUI
    async_set_service_schema(
        hass,
        NOTIFY_DOMAIN,
        service_name,
        {
            "name": "Send message",
            "description": "Send a Signal message to one or more recipients",
            "fields": {
                "message": {
                    "name": "Message",
                    "description": "The message content to send",
                    "required": True,
                    "example": "Hello from Home Assistant!",
                    "selector": {"text": {"multiline": True}},
                },
                "title": {
                    "name": "Title",
                    "description": "Optional title that will be prepended to the message",
                    "required": False,
                    "example": "Alert",
                    "selector": {"text": {}},
                },
                "target": {
                    "name": "Target",
                    "description": (
                        "Phone number (with country code) or group ID. "
                        "Can be a single value or a list. If not provided, "
                        "uses default recipients from configuration."
                    ),
                    "required": False,
                    "example": "+1234567890",
                    "selector": {"text": {}},
                },
                "attachments": {
                    "name": "Attachments",
                    "description": "List of local file paths to attach to the message",
                    "required": False,
                    "example": ["/config/www/camera_snapshot.jpg"],
                    "selector": {"object": {}},
                },
                "urls": {
                    "name": "URLs",
                    "description": "List of URLs to download and attach to the message",
                    "required": False,
                    "example": ["https://example.com/image.jpg"],
                    "selector": {"object": {}},
                },
                "verify_ssl": {
                    "name": "Verify SSL",
                    "description": "Verify SSL certificates when downloading URLs (default: true)",
                    "required": False,
                    "selector": {"boolean": {}},
                },
                "text_mode": {
                    "name": "Text Mode",
                    "description": (
                        "Text formatting mode: 'styled' enables markdown-like formatting "
                        "(*italic*, **bold**, ~strikethrough~, `monospace`, ||spoiler||). "
                        "Default: 'normal' (plain text, compatible with official integration)"
                    ),
                    "required": False,
                    "example": "normal",
                    "selector": {"select": {"options": ["normal", "styled"]}},
                },
            },
        },
    )
    return True


async def async_unload_notify_service(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Signal Gateway notify entry."""
    # Note: this could be a "async_unload_entry" called when "async_forward_entry_setups"
    # is called in __init__.py
    # however this do not work with the notify platform so we do it manually here
    _LOGGER.info("Unloading Signal Gateway notify entry %s", entry.entry_id)
    data = hass.data[DOMAIN].get(entry.entry_id, {})
    service_name = data.get("service_name")

    if service_name:
        _LOGGER.debug(
            "Unregistering Signal Gateway notify service '%s' for entry %s",
            service_name,
            entry.entry_id,
        )
        hass.services.async_remove(NOTIFY_DOMAIN, service_name)

    return True


class SignalGatewayNotificationService(BaseNotificationService):
    """Signal Gateway notification service for Home Assistant."""

    def __init__(
        self, hass: HomeAssistant, client: SignalClient, default_recipients: list[str]
    ) -> None:
        """Initialize the notification service."""
        self.hass = hass
        self._client: SignalClient = client
        self._default_recipients: list[str] = default_recipients

    def send_message(self, message, **kwargs):
        raise NotImplementedError("Use async_send_message instead")

    @staticmethod
    def _fix_phone_number(recipient: str) -> str:
        """
        Fix phone number format by ensuring it has a '+' prefix.

        Home Assistant may interpret phone numbers as integers in certain contexts,
        which strips the leading '+' sign. This function restores the '+' prefix
        for phone numbers that are all digits but missing it.

        Args:
            recipient (str): The phone number to fix, with or without '+' prefix.

        Returns:
            str: The phone number with '+' prefix added if it was missing.

        Examples:
            >>> SignalGatewayNotificationService._fix_phone_number("+1234567890")
            '+1234567890'

            >>> SignalGatewayNotificationService._fix_phone_number("1234567890")
            '+1234567890'

            >>> SignalGatewayNotificationService._fix_phone_number("+44123456")
            '+44123456'

            >>> SignalGatewayNotificationService._fix_phone_number("notanumber")
            'notanumber'
        """
        # Home Assistant phone numbers may not include the '+' prefix
        if not recipient.startswith("+") and recipient.isdigit():
            recipient = f"+{recipient}"
        return recipient

    def _normalize_file_path(self, file_path: str) -> Path:
        """Normalize and validate a file path.

        Args:
            file_path: File path to normalize (supports file:// URLs)

        Returns:
            Validated Path object

        Raises:
            ValueError: If the file doesn't exist, isn't readable, or exceeds size limit
        """
        # Handle file:// URLs
        if file_path.startswith("file://"):
            file_path = file_path[7:]

        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Attachment file not found: {file_path}")
        if not path.is_file():
            raise ValueError(f"Attachment path is not a file: {file_path}")
        if not os.access(path, os.R_OK):
            raise ValueError(f"Attachment file is not readable: {file_path}")

        # Check file size
        file_size = path.stat().st_size
        if file_size > CONF_MAX_ALLOWED_DOWNLOAD_SIZE_BYTES:
            raise ValueError(
                f"Attachment file {file_path} size ({file_size} bytes) "
                f"exceeds maximum allowed size ({CONF_MAX_ALLOWED_DOWNLOAD_SIZE_BYTES} bytes)"
            )

        return path

    def _encode_file_to_base64(self, path: Path) -> str:
        """Read a file and encode it as base64.

        Args:
            path: Path to the file to encode

        Returns:
            Base64 encoded file contents

        Raises:
            OSError: If the file cannot be read
        """
        with open(path, "rb") as f:
            file_content = f.read()
            base64_content = str(base64.b64encode(file_content), encoding="utf-8")
            _LOGGER.debug(
                "Encoded attachment %s (%d bytes, %d base64 chars)",
                path.name,
                len(file_content),
                len(base64_content),
            )
            return base64_content

    def _encode_attachments_from_paths(self, file_paths: list[str]) -> list[str]:
        """Validate file paths and encode them as base64.

        Args:
            file_paths: List of file paths to encode

        Returns:
            List of base64 encoded file contents

        Raises:
            ValueError: If a file doesn't exist or isn't readable
        """
        base64_attachments = []
        for file_path in file_paths:
            path = self._normalize_file_path(file_path)
            base64_content = self._encode_file_to_base64(path)
            base64_attachments.append(base64_content)

        return base64_attachments

    def _validate_content_length(
        self, content_length: Optional[str], max_size: int
    ) -> None:
        """Validate the Content-Length header against max size.

        Args:
            content_length: Content-Length header value
            max_size: Maximum allowed size in bytes

        Raises:
            ValueError: If content length exceeds max size
        """
        if content_length:
            size = int(content_length)
            if size > max_size:
                raise ValueError(
                    f"Attachment too large (Content-Length: {size} bytes). "
                    f"Max size: {max_size} bytes"
                )

    async def _download_in_chunks(
        self, response: aiohttp.ClientResponse, max_size: int
    ) -> bytes:
        """Download response content in chunks with size validation.

        Args:
            response: aiohttp response to download from
            max_size: Maximum allowed download size in bytes

        Returns:
            Downloaded content as bytes

        Raises:
            ValueError: If downloaded size exceeds max size
        """
        size = 0
        chunks = bytearray()
        async for chunk in response.content.iter_chunked(1024):
            size += len(chunk)
            if size > max_size:
                raise ValueError(
                    f"Attachment too large (downloaded: {size} bytes). "
                    f"Max size: {max_size} bytes"
                )
            chunks.extend(chunk)
        return bytes(chunks)

    async def _download_and_encode_url(
        self, session: aiohttp.ClientSession, url: str, max_size: int
    ) -> str:
        """Download a file from URL and encode it as base64.

        Args:
            session: aiohttp session to use for download
            url: URL to download from
            max_size: Maximum allowed download size in bytes

        Returns:
            Base64 encoded file contents

        Raises:
            ValueError: If download fails or file is too large
        """
        _LOGGER.debug("Downloading attachment from URL: %s", url)
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()

            # Validate Content-Length if available
            self._validate_content_length(resp.headers.get("Content-Length"), max_size)

            # Download in chunks
            chunks = await self._download_in_chunks(resp, max_size)

            # Encode as base64
            base64_content = str(base64.b64encode(chunks), encoding="utf-8")
            _LOGGER.debug(
                "Downloaded and encoded attachment from %s (%d bytes, %d base64 chars)",
                url,
                len(chunks),
                len(base64_content),
            )
            return base64_content

    async def _download_attachments_from_urls(
        self,
        urls: list[str],
        verify_ssl: bool = True,
        max_size: int = CONF_MAX_ALLOWED_DOWNLOAD_SIZE_BYTES,
    ) -> Optional[list[str]]:
        """Download attachments from URLs and encode as base64.

        Args:
            urls: List of URLs to download
            verify_ssl: Whether to verify SSL certificates
            max_size: Maximum allowed download size in bytes

        Returns:
            List of base64 encoded file contents

        Raises:
            ValueError: If file is too large (raised by sub-methods)
            aiohttp.ClientError: If download fails (network/HTTP errors)
        """
        base64_attachments = []
        session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)

        for url in urls:
            base64_content = await self._download_and_encode_url(session, url, max_size)
            base64_attachments.append(base64_content)

        return base64_attachments if base64_attachments else None

    def _normalize_targets(
        self, target: Optional[Union[str, list[str]]]
    ) -> Optional[list[str]]:
        """Normalize target parameter to a list of recipients.

        Args:
            target: Single target or list of targets

        Returns:
            List of target recipients, or None if validation fails
        """
        if not target:
            if not self._default_recipients:
                _LOGGER.error(
                    "Target (phone number or group ID) is required "
                    "and no default recipients configured"
                )
                return None
            return self._default_recipients

        # Ensure target is a list
        if isinstance(target, str):
            return [target]
        return target

    def _prepare_message(self, message: str, title: Optional[str]) -> str:
        """Prepare the full message with optional title.

        Args:
            message: The message content
            title: Optional title to prepend

        Returns:
            Full message with title prepended if provided
        """
        if title:
            return f"{title}\n{message}"
        return message

    async def _process_attachments(
        self,
        attachments: Optional[list[Any]],
        urls: Optional[list[str]],
        verify_ssl: bool,
    ) -> Optional[list[str]]:
        """Process and encode all attachments from files and URLs.

        Args:
            attachments: List of local file paths
            urls: List of URLs to download
            verify_ssl: Whether to verify SSL certificates

        Returns:
            List of base64 encoded attachments, or None if no attachments

        Raises:
            ValueError: If file validation fails (not found, too large, not readable)
            OSError: If file I/O fails
            aiohttp.ClientError: If URL download fails

        Note:
            Exceptions are propagated to notify the user of attachment failures.
            Message will not be sent if attachment processing fails.
        """
        base64_attachments = []

        # Encode local file paths to base64
        if attachments:
            local_base64 = self._encode_attachments_from_paths(attachments)
            base64_attachments.extend(local_base64)
            _LOGGER.debug("Encoded %d local attachments", len(local_base64))

        # Download from URLs and encode to base64
        if urls:
            url_base64 = await self._download_attachments_from_urls(urls, verify_ssl)
            if url_base64:
                base64_attachments.extend(url_base64)
                _LOGGER.debug(
                    "Downloaded and encoded %d attachments from URLs",
                    len(url_base64),
                )

        return base64_attachments if base64_attachments else None

    async def _send_to_recipient(
        self,
        recipient: str,
        message: str,
        base64_attachments: Optional[list[str]],
        text_mode: str = "normal",
    ) -> None:
        """Send a message to a single recipient.

        Args:
            recipient: Target phone number or group ID
            message: Message to send
            base64_attachments: Optional list of base64 encoded attachments
            text_mode: Text formatting mode (\"normal\" or \"styled\", default: \"normal\")

        Note:
            Logs errors but does not raise to allow sending to other recipients.
        """
        try:
            recipient = self._fix_phone_number(recipient)
            result = await self._client.send_message(
                target=recipient,
                message=message,
                base64_attachments=base64_attachments,
                text_mode=text_mode,
            )
            _LOGGER.info("Notification sent successfully to %s", recipient)
            _LOGGER.debug("Send result: %s", result)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.error(
                "Failed to send notification to %s: %s", recipient, err, exc_info=True
            )

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def async_send_message(
        self,
        message: Optional[str] = None,
        title: Optional[str] = None,
        target: Optional[Union[str, list[str]]] = None,
        attachments: Optional[list[Any]] = None,
        urls: Optional[list[str]] = None,
        verify_ssl: bool = True,
        text_mode: str = "normal",
        **kwargs: Any,
    ) -> None:
        """Send a notification via Signal.

        Args:
            message: The message to send
            title: Optional title (prepended to message)
            target: Phone number or group ID
            attachments: List of local file paths to attach
            urls: List of URLs to download and attach
            verify_ssl: Whether to verify SSL certificates when downloading URLs
            text_mode: Text formatting mode (\"normal\" or \"styled\", default: \"normal\")
        """
        if not message:
            _LOGGER.error("Message is required")
            return

        # Normalize targets
        targets = self._normalize_targets(target)
        if targets is None:
            return

        # Prepare message
        full_message = self._prepare_message(message, title)

        # Process attachments (will raise exception on failure)
        base64_attachments = await self._process_attachments(
            attachments, urls, verify_ssl
        )

        # Send to each recipient
        for recipient in targets:
            await self._send_to_recipient(
                recipient, full_message, base64_attachments, text_mode
            )
