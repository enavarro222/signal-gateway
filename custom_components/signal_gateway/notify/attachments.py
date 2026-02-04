"""Attachment processing for Signal Gateway notify service."""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Any, Optional

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

# Attachment constraints
MAX_ALLOWED_DOWNLOAD_SIZE_BYTES = 52428800  # 50 MB


class AttachmentProcessor:
    """Process and encode attachments from local files and URLs."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the attachment processor.

        Args:
            hass: Home Assistant instance
        """
        self.hass = hass

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
        if file_size > MAX_ALLOWED_DOWNLOAD_SIZE_BYTES:
            raise ValueError(
                f"Attachment file {file_path} size ({file_size} bytes) "
                f"exceeds maximum allowed size ({MAX_ALLOWED_DOWNLOAD_SIZE_BYTES} bytes)"
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

    def encode_attachments_from_paths(self, file_paths: list[str]) -> list[str]:
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

    async def download_attachments_from_urls(
        self,
        urls: list[str],
        verify_ssl: bool = True,
        max_size: int = MAX_ALLOWED_DOWNLOAD_SIZE_BYTES,
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

    async def process_attachments(
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
            local_base64 = self.encode_attachments_from_paths(attachments)
            base64_attachments.extend(local_base64)
            _LOGGER.debug("Encoded %d local attachments", len(local_base64))

        # Download from URLs and encode to base64
        if urls:
            url_base64 = await self.download_attachments_from_urls(urls, verify_ssl)
            if url_base64:
                base64_attachments.extend(url_base64)
                _LOGGER.debug(
                    "Downloaded and encoded %d attachments from URLs",
                    len(url_base64),
                )

        return base64_attachments if base64_attachments else None
