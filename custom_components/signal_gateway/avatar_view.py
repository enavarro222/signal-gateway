"""HTTP view for serving Signal avatars."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import TYPE_CHECKING
import secrets

from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Token valid for 1 hour
TOKEN_EXPIRATION_SECONDS = 3600


def _get_secret(hass: HomeAssistant) -> str:
    """Get the secret key for signing tokens.

    Args:
        hass: Home Assistant instance

    Returns:
        Secret key as string
    """
    if not hasattr(hass.data, "secret"):
        # Generate a secret for this session if not available
        if "avatar_secret" not in hass.data:
            hass.data["avatar_secret"] = secrets.token_hex(32)
        return hass.data["avatar_secret"]
    return str(hass.data.get("secret", hass.config.path("secret")))


def generate_avatar_token(
    hass: HomeAssistant, entry_id: str, device_id: str
) -> tuple[str, int]:
    """Generate a secure time-based token for avatar access.

    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        device_id: Contact UUID or group ID

    Returns:
        Tuple of (token, expiration_timestamp)
    """
    secret = _get_secret(hass)

    # Create expiration timestamp (current time + 1 hour)
    expires = int(time.time()) + TOKEN_EXPIRATION_SECONDS

    # Sign the message with expiration time
    message = f"{entry_id}:{device_id}:{expires}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()

    # Token format: signature[:16]:expires
    token = f"{signature[:16]}:{expires}"
    return token, expires


def validate_avatar_token(
    hass: HomeAssistant, entry_id: str, device_id: str, token: str
) -> bool:
    """Validate a time-based avatar token.

    Args:
        hass: Home Assistant instance
        entry_id: Config entry ID
        device_id: Contact UUID or group ID
        token: Token to validate (format: "signature:timestamp")

    Returns:
        True if token is valid and not expired
    """
    # Parse token
    parts = token.split(":")
    if len(parts) != 2:
        return False

    provided_sig, expires_str = parts

    try:
        expires = int(expires_str)
    except ValueError:
        _LOGGER.debug("Invalid avatar token timestamp: %s", expires_str)
        return False

    # Check if token has expired
    if time.time() > expires:
        _LOGGER.debug("Avatar token expired for entry %s", entry_id)
        return False

    # Regenerate expected signature
    secret = _get_secret(hass)
    message = f"{entry_id}:{device_id}:{expires}".encode("utf-8")
    expected_sig = hmac.new(
        secret.encode("utf-8"), message, hashlib.sha256
    ).hexdigest()[:16]

    # Use constant-time comparison
    return hmac.compare_digest(provided_sig, expected_sig)


class SignalAvatarView(HomeAssistantView):
    """View to serve Signal contact and group avatars."""

    url = "/api/signal_gateway/{entry_id}/avatar/{device_type}/{device_id}"
    name = "api:signal_gateway:avatar"
    requires_auth = False  # Use token-based auth with expiration instead

    async def get(
        self, request: web.Request, entry_id: str, device_type: str, device_id: str
    ) -> web.Response:
        """Serve avatar image.

        Args:
            request: HTTP request
            entry_id: Config entry ID
            device_type: "contact" or "group"
            device_id: Contact UUID or group ID

        Returns:
            Image response or 404/403
        """
        hass: HomeAssistant = request.app["hass"]

        # Validate token for security
        token = request.query.get("token")
        if not token or not validate_avatar_token(hass, entry_id, device_id, token):
            _LOGGER.warning(
                "Invalid or expired avatar token from %s for entry %s",
                request.remote,
                entry_id,
            )
            return web.Response(status=403, text="Forbidden")

        # Verify the entry exists and is accessible
        if DOMAIN not in hass.data or entry_id not in hass.data[DOMAIN]:
            _LOGGER.warning(
                "Avatar request for unknown entry %s from %s",
                entry_id,
                request.remote,
            )
            return web.Response(status=404, text="Entry not found")

        client = hass.data[DOMAIN][entry_id]["client"]

        try:
            if device_type == "contact":
                avatar_bytes = await client.get_contact_avatar(device_id)
            elif device_type == "group":
                avatar_bytes = await client.get_group_avatar(device_id)
            else:
                return web.Response(status=400, text="Invalid device type")

            # Return the image with appropriate content type
            return web.Response(
                body=avatar_bytes,
                content_type="image/png",
                headers={"Cache-Control": "private, max-age=3600"},
            )
        except Exception as err:  # pylint: disable=broad-except
            # Log the actual error for debugging (401, 404, etc.)
            _LOGGER.warning(
                "Failed to fetch %s avatar %s: %s (type: %s)",
                device_type,
                device_id,
                err,
                type(err).__name__,
            )
            return web.Response(status=404, text="Avatar not found")


def setup_avatar_view(hass: HomeAssistant) -> None:
    """Set up the avatar view.

    Args:
        hass: Home Assistant instance
    """
    hass.http.register_view(SignalAvatarView())
