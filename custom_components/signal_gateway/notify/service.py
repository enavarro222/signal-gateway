"""Signal Gateway notification service class."""

from __future__ import annotations

import logging
from typing import Any, Optional, Union

from homeassistant.core import HomeAssistant

from ..signal import SignalClient
from .attachments import AttachmentProcessor
from .helpers import fix_phone_number, normalize_targets, prepare_message

_LOGGER = logging.getLogger(__name__)


class SignalGatewayNotificationService:
    """Signal Gateway notification service for Home Assistant."""

    def __init__(
        self, hass: HomeAssistant, client: SignalClient, default_recipients: list[str]
    ) -> None:
        """Initialize the notification service.

        Args:
            hass: Home Assistant instance
            client: Signal client instance
            default_recipients: Default recipients for notifications
        """
        self.hass = hass
        self._client: SignalClient = client
        self._default_recipients: list[str] = default_recipients
        self._attachment_processor = AttachmentProcessor(hass)

    async def handle_service_call(self, call) -> None:
        """Handle a service call from Home Assistant.

        Args:
            call: Service call data from Home Assistant

        Note:
            This extracts nested data parameters to match the official
            signal_messenger integration's service call format.
        """
        _LOGGER.debug(
            "Sending message to target=%s, message starts with: %s",
            call.data.get("target"),
            call.data.get("message", "")[:50],
        )
        # Extract nested data parameters (matches official signal_messenger integration)
        data_params = call.data.get("data", {})
        await self.async_send_message(
            message=call.data.get("message"),
            title=call.data.get("title"),
            target=call.data.get("target"),
            attachments=data_params.get("attachments"),
            urls=data_params.get("urls"),
            verify_ssl=data_params.get("verify_ssl", True),
            text_mode=data_params.get("text_mode", "normal"),
        )

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
            text_mode: Text formatting mode ("normal" or "styled", default: "normal")

        Note:
            Logs errors but does not raise to allow sending to other recipients.
        """
        try:
            recipient = fix_phone_number(recipient)
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

    # pylint: disable=too-many-arguments,too-many-positional-arguments,unused-argument
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
            text_mode: Text formatting mode ("normal" or "styled", default: "normal")
        """
        if not message:
            _LOGGER.error("Message is required")
            return

        # Normalize targets
        targets = normalize_targets(target, self._default_recipients)
        if targets is None:
            return

        # Prepare message
        full_message = prepare_message(message, title)

        # Process attachments (will raise exception on failure)
        base64_attachments = await self._attachment_processor.process_attachments(
            attachments, urls, verify_ssl
        )

        # Send to each recipient
        for recipient in targets:
            await self._send_to_recipient(
                recipient, full_message, base64_attachments, text_mode
            )
