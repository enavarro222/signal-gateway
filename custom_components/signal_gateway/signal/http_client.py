"""HTTP client for Signal-cli-rest-api."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

import aiohttp

from .models import SignalContact, SignalGroup

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
        text_mode: str = "normal",
    ) -> dict[str, Any]:
        """Send a message via Signal.

        Args:
            target: Phone number or group ID to send to
            message: Message text to send
            base64_attachments: Optional list of base64 encoded attachments
            text_mode: Text formatting mode ("normal" or "styled", default: "normal")

        Returns:
            Response from the API
        """
        payload = {
            "recipients": [
                target,
            ],
            "message": message,
            "number": self.phone_number,
            "text_mode": text_mode,
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
                    raise RuntimeError(
                        f"Signal API error: {response.status} - {response_text}"
                    )

                try:
                    return await response.json()
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    # If JSON parsing fails, return the text
                    _LOGGER.warning("Response is not valid JSON: %s", response_text)
                    return {"success": True, "response": response_text}
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Signal API: %s", err)
            raise

    # Groups API

    async def list_groups(self) -> list[SignalGroup]:
        """List all Signal groups.

        Returns:
            List of SignalGroup objects

        Raises:
            aiohttp.ClientError: If the request fails
        """
        try:
            async with self.session.get(
                f"{self.api_url}/v1/groups/{self.phone_number}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return [SignalGroup.from_api(group) for group in data]
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching groups: %s", err)
            raise

    async def get_group(self, group_id: str) -> SignalGroup:
        """Get details for a specific Signal group.

        Args:
            group_id: The Signal group ID

        Returns:
            SignalGroup object

        Raises:
            aiohttp.ClientError: If the request fails
        """
        try:
            async with self.session.get(
                f"{self.api_url}/v1/groups/{self.phone_number}/{group_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return SignalGroup.from_api(data)
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching group %s: %s", group_id, err)
            raise

    async def create_group(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        name: str,
        members: list[str],
        description: str = "",
        permissions: Optional[dict[str, str]] = None,
        group_link: str = "disabled",
    ) -> str:
        """Create a new Signal group.

        Args:
            name: Group name
            members: List of member phone numbers
            description: Group description
            permissions: Group permissions dict
            group_link: Group link setting ("disabled", "enabled", "enabled-with-approval")

        Returns:
            The created group ID

        Raises:
            aiohttp.ClientError: If the request fails
        """
        payload: dict[str, Any] = {
            "name": name,
            "members": members,
        }

        if description:
            payload["description"] = description

        if permissions:
            payload["permissions"] = permissions

        if group_link:
            payload["group_link"] = group_link

        try:
            async with self.session.post(
                f"{self.api_url}/v1/groups/{self.phone_number}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("id", "")
        except aiohttp.ClientError as err:
            _LOGGER.error("Error creating group: %s", err)
            raise

    async def update_group(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        group_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[dict[str, str]] = None,
        group_link: Optional[str] = None,
    ) -> None:
        """Update a Signal group.

        Args:
            group_id: The Signal group ID
            name: New group name
            description: New group description
            permissions: New group permissions
            group_link: New group link setting

        Raises:
            aiohttp.ClientError: If the request fails
        """
        payload: dict[str, Any] = {}

        if name is not None:
            payload["name"] = name
        if description is not None:
            payload["description"] = description
        if permissions is not None:
            payload["permissions"] = permissions
        if group_link is not None:
            payload["group_link"] = group_link

        if not payload:
            _LOGGER.warning("No updates provided for group %s", group_id)
            return

        try:
            async with self.session.put(
                f"{self.api_url}/v1/groups/{self.phone_number}/{group_id}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error updating group %s: %s", group_id, err)
            raise

    async def delete_group(self, group_id: str) -> None:
        """Delete a Signal group.

        Args:
            group_id: The Signal group ID

        Raises:
            aiohttp.ClientError: If the request fails
        """
        try:
            async with self.session.delete(
                f"{self.api_url}/v1/groups/{self.phone_number}/{group_id}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error deleting group %s: %s", group_id, err)
            raise

    async def add_group_members(self, group_id: str, members: list[str]) -> None:
        """Add members to a Signal group.

        Args:
            group_id: The Signal group ID
            members: List of phone numbers to add

        Raises:
            aiohttp.ClientError: If the request fails
        """
        payload = {"members": members}

        try:
            async with self.session.post(
                f"{self.api_url}/v1/groups/{self.phone_number}/{group_id}/members",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error adding members to group %s: %s", group_id, err)
            raise

    async def remove_group_members(self, group_id: str, members: list[str]) -> None:
        """Remove members from a Signal group.

        Args:
            group_id: The Signal group ID
            members: List of phone numbers to remove

        Raises:
            aiohttp.ClientError: If the request fails
        """
        payload = {"members": members}

        try:
            async with self.session.delete(
                f"{self.api_url}/v1/groups/{self.phone_number}/{group_id}/members",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error removing members from group %s: %s", group_id, err)
            raise

    async def add_group_admins(self, group_id: str, admins: list[str]) -> None:
        """Add admins to a Signal group.

        Args:
            group_id: The Signal group ID
            admins: List of phone numbers to make admins

        Raises:
            aiohttp.ClientError: If the request fails
        """
        payload = {"admins": admins}

        try:
            async with self.session.post(
                f"{self.api_url}/v1/groups/{self.phone_number}/{group_id}/admins",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error adding admins to group %s: %s", group_id, err)
            raise

    async def remove_group_admins(self, group_id: str, admins: list[str]) -> None:
        """Remove admins from a Signal group.

        Args:
            group_id: The Signal group ID
            admins: List of phone numbers to remove as admins

        Raises:
            aiohttp.ClientError: If the request fails
        """
        payload = {"admins": admins}

        try:
            async with self.session.delete(
                f"{self.api_url}/v1/groups/{self.phone_number}/{group_id}/admins",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error removing admins from group %s: %s", group_id, err)
            raise

    # Contacts API

    async def list_contacts(self) -> list[SignalContact]:
        """List all contacts.

        Returns:
            List of SignalContact objects

        Raises:
            aiohttp.ClientError: If the request fails
        """
        try:
            async with self.session.get(
                f"{self.api_url}/v1/contacts/{self.phone_number}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return [SignalContact.from_api(contact) for contact in data]
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching contacts: %s", err)
            raise

    async def get_contact(self, uuid: str) -> SignalContact:
        """Get details for a specific contact.

        Args:
            uuid: The contact's UUID

        Returns:
            SignalContact object

        Raises:
            aiohttp.ClientError: If the request fails
        """
        try:
            async with self.session.get(
                f"{self.api_url}/v1/contacts/{self.phone_number}/{uuid}",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return SignalContact.from_api(data)
        except aiohttp.ClientError as err:
            _LOGGER.error("Error fetching contact %s: %s", uuid, err)
            raise

    async def update_contact(
        self,
        recipient: str,
        name: Optional[str] = None,
        expiration_in_seconds: int = 0,
    ) -> None:
        """Update or add a contact.

        Args:
            recipient: Phone number or UUID
            name: Contact name
            expiration_in_seconds: Message expiration time

        Raises:
            aiohttp.ClientError: If the request fails
        """
        payload: dict[str, Any] = {
            "recipient": recipient,
        }

        if name is not None:
            payload["name"] = name

        if expiration_in_seconds > 0:
            payload["expiration_in_seconds"] = expiration_in_seconds

        try:
            async with self.session.put(
                f"{self.api_url}/v1/contacts/{self.phone_number}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
        except aiohttp.ClientError as err:
            _LOGGER.error("Error updating contact %s: %s", recipient, err)
            raise
