"""HTTP client for Signal-cli-rest-api."""

from __future__ import annotations

import logging
from typing import Any, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class SignalHTTPClient:
    """HTTP client for Signal-cli-rest-api.

    See https://github.com/bbernhard/signal-cli-rest-api
    """

    def __init__(self, api_url: str, phone_number: str, session: aiohttp.ClientSession):
        """Initialize the HTTP client."""
        self.api_url = api_url.rstrip("/")
        self.phone_number = phone_number
        self.session = session

    async def send_message(
        self,
        target: str,
        message: str,
        base64_attachments: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Send a message via Signal.

        Args:
            target: Phone number or group ID to send to
            message: Message text to send
            base64_attachments: Optional list of base64 encoded attachments

        Returns:
            Response from the API
        """
        payload = {
            "recipients": [
                target,
            ],
            "message": message,
            "number": self.phone_number,
        }

        if base64_attachments:
            payload["base64_attachments"] = base64_attachments

        _LOGGER.debug(
            "Sending message to %s (message length: %d, attachments: %d)",
            target,
            len(message),
            len(base64_attachments) if base64_attachments else 0,
        )

        try:
            async with self.session.post(
                f"{self.api_url}/v2/send",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response_text = await response.text()

                if response.status >= 300:
                    _LOGGER.error(
                        "Signal API error: %s - %s",
                        response.status,
                        response_text,
                    )
                    _LOGGER.debug(
                        "Failed request payload: recipients=%s, message_len=%d, attachments=%d",
                        payload["recipients"],
                        len(payload["message"]),
                        len(payload.get("base64_attachments", [])),
                    )
                    raise Exception(
                        f"Signal API error: {response.status} - {response_text}"
                    )

                try:
                    return await response.json()
                except Exception:
                    # If JSON parsing fails, return the text
                    _LOGGER.warning("Response is not valid JSON: %s", response_text)
                    return {"success": True, "response": response_text}
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Signal API: %s", err)
            raise
