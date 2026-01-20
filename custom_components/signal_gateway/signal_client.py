"""Signal CLI REST API client using aiohttp."""

from __future__ import annotations

import logging
from typing import Any, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)


class SignalClient:
    """Minimal HTTP client for Signal-cli-rest-api.

    See https://github.com/bbernhard/signal-cli-rest-api
    """

    def __init__(self, api_url: str, phone_number: str, session: aiohttp.ClientSession):
        """Initialize the Signal client."""
        self.api_url = api_url.rstrip("/")
        self.number = phone_number
        self.session = session

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
        payload = {
            "recipients": [
                target,
            ],
            "message": message,
            "number": self.number,
        }

        if attachments:
            payload["attachments"] = attachments

        try:
            async with self.session.post(
                f"{self.api_url}/v2/send",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status >= 300:
                    error_text = await response.text()
                    _LOGGER.error(
                        "Signal API error: %s - %s",
                        response.status,
                        error_text,
                    )
                    raise Exception(
                        f"Signal API error: {response.status} - {error_text}"
                    )

                return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Signal API: %s", err)
            raise
