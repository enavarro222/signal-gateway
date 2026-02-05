"""Tests for avatar view."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.signal_gateway.avatar_view import (
    SignalAvatarView,
    generate_avatar_token,
    setup_avatar_view,
    validate_avatar_token,
)
from custom_components.signal_gateway.const import DOMAIN


@pytest.fixture
def mock_avatar_client():
    """Create a mock Signal client with avatar methods."""
    from unittest.mock import AsyncMock

    client = MagicMock()
    client.get_contact_avatar = AsyncMock(return_value=b"fake_contact_image_data")
    client.get_group_avatar = AsyncMock(return_value=b"fake_group_image_data")
    return client


@pytest.fixture
def mock_request(mock_hass):
    """Create a mock aiohttp request."""
    request = MagicMock()
    request.app = {"hass": mock_hass}
    request.remote = "127.0.0.1"
    request.query = {}
    return request


def test_generate_avatar_token(mock_hass):
    """Test token generation."""
    entry_id = "test_entry"
    device_id = "test_device"

    token, expires = generate_avatar_token(mock_hass, entry_id, device_id)

    # Token should have the format "signature:timestamp"
    assert ":" in token
    parts = token.split(":")
    assert len(parts) == 2
    assert len(parts[0]) == 16  # Signature is truncated to 16 chars
    assert int(parts[1]) == expires
    assert expires > time.time()


def test_validate_avatar_token_valid(mock_hass):
    """Test token validation with a valid token."""
    entry_id = "test_entry"
    device_id = "test_device"

    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)

    assert validate_avatar_token(mock_hass, entry_id, device_id, token) is True


def test_validate_avatar_token_wrong_device(mock_hass):
    """Test token validation fails with wrong device ID."""
    entry_id = "test_entry"
    device_id = "test_device"

    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)

    # Try to use the token with a different device
    assert (
        validate_avatar_token(mock_hass, entry_id, "different_device", token) is False
    )


def test_validate_avatar_token_wrong_entry(mock_hass):
    """Test token validation fails with wrong entry ID."""
    entry_id = "test_entry"
    device_id = "test_device"

    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)

    # Try to use the token with a different entry
    assert (
        validate_avatar_token(mock_hass, "different_entry", device_id, token) is False
    )


def test_validate_avatar_token_expired(mock_hass):
    """Test token validation fails with expired token."""
    entry_id = "test_entry"
    device_id = "test_device"

    # Create a token that expired 1 second ago
    with patch("time.time", return_value=time.time() - 3601):
        token, _ = generate_avatar_token(mock_hass, entry_id, device_id)

    # Token should be expired now
    assert validate_avatar_token(mock_hass, entry_id, device_id, token) is False


def test_validate_avatar_token_malformed(mock_hass):
    """Test token validation fails with malformed token."""
    mock_hass.data = {"avatar_secret": "test_secret"}

    # Token without colon
    assert validate_avatar_token(mock_hass, "entry", "device", "invalid") is False

    # Token with too many parts
    assert validate_avatar_token(mock_hass, "entry", "device", "a:b:c") is False

    # Token with non-numeric timestamp
    assert (
        validate_avatar_token(mock_hass, "entry", "device", "abc:notanumber") is False
    )


@pytest.mark.asyncio
async def test_avatar_view_contact_success(mock_request, mock_hass, mock_avatar_client):
    """Test successful contact avatar retrieval."""
    entry_id = "test_entry"
    device_id = "contact_123"

    # Setup hass data
    mock_hass.data[DOMAIN] = {entry_id: {"client": mock_avatar_client}}

    # Generate valid token
    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)
    mock_request.query = {"token": token}

    # Call the view
    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "contact", device_id)

    assert response.status == 200
    assert response.body == b"fake_contact_image_data"
    assert response.content_type == "image/png"
    assert "Cache-Control" in response.headers
    mock_avatar_client.get_contact_avatar.assert_called_once_with(device_id)


@pytest.mark.asyncio
async def test_avatar_view_group_success(mock_request, mock_hass, mock_avatar_client):
    """Test successful group avatar retrieval."""
    entry_id = "test_entry"
    device_id = "group_456"

    # Setup hass data
    mock_hass.data[DOMAIN] = {entry_id: {"client": mock_avatar_client}}

    # Generate valid token
    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)
    mock_request.query = {"token": token}

    # Call the view
    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "group", device_id)

    assert response.status == 200
    assert response.body == b"fake_group_image_data"
    assert response.content_type == "image/png"
    mock_avatar_client.get_group_avatar.assert_called_once_with(device_id)


@pytest.mark.asyncio
async def test_avatar_view_no_token(mock_request, mock_hass):
    """Test avatar request without token returns 403."""
    entry_id = "test_entry"
    device_id = "contact_123"

    # No token in query
    mock_request.query = {}

    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "contact", device_id)

    assert response.status == 403
    assert response.text == "Forbidden"


@pytest.mark.asyncio
async def test_avatar_view_invalid_token(mock_request, mock_hass):
    """Test avatar request with invalid token returns 403."""
    entry_id = "test_entry"
    device_id = "contact_123"

    # Invalid token
    mock_request.query = {"token": "invalid_token:12345"}

    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "contact", device_id)

    assert response.status == 403
    assert response.text == "Forbidden"


@pytest.mark.asyncio
async def test_avatar_view_expired_token(mock_request, mock_hass):
    """Test avatar request with expired token returns 403."""
    entry_id = "test_entry"
    device_id = "contact_123"

    # Create expired token
    with patch("time.time", return_value=time.time() - 3601):
        token, _ = generate_avatar_token(mock_hass, entry_id, device_id)

    mock_request.query = {"token": token}

    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "contact", device_id)

    assert response.status == 403
    assert response.text == "Forbidden"


@pytest.mark.asyncio
async def test_avatar_view_entry_not_found(mock_request, mock_hass):
    """Test avatar request for non-existent entry returns 404."""
    entry_id = "nonexistent_entry"
    device_id = "contact_123"

    # Setup empty hass data
    mock_hass.data[DOMAIN] = {}

    # Generate valid token
    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)
    mock_request.query = {"token": token}

    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "contact", device_id)

    assert response.status == 404
    assert response.text == "Entry not found"


@pytest.mark.asyncio
async def test_avatar_view_invalid_device_type(
    mock_request, mock_hass, mock_avatar_client
):
    """Test avatar request with invalid device type returns 400."""
    entry_id = "test_entry"
    device_id = "device_123"

    # Setup hass data
    mock_hass.data[DOMAIN] = {entry_id: {"client": mock_avatar_client}}

    # Generate valid token
    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)
    mock_request.query = {"token": token}

    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "invalid_type", device_id)

    assert response.status == 400
    assert response.text == "Invalid device type"


@pytest.mark.asyncio
async def test_avatar_view_client_error(mock_request, mock_hass, mock_avatar_client):
    """Test avatar retrieval when client raises exception."""
    entry_id = "test_entry"
    device_id = "contact_123"

    # Setup hass data
    mock_hass.data[DOMAIN] = {entry_id: {"client": mock_avatar_client}}

    # Make client raise an exception
    mock_avatar_client.get_contact_avatar.side_effect = Exception("API Error")

    # Generate valid token
    token, _ = generate_avatar_token(mock_hass, entry_id, device_id)
    mock_request.query = {"token": token}

    view = SignalAvatarView()
    response = await view.get(mock_request, entry_id, "contact", device_id)

    assert response.status == 404
    assert response.text == "Avatar not found"


def test_setup_avatar_view_with_http(mock_hass):
    """Test setting up avatar view with HTTP component available."""
    mock_hass.http = MagicMock()

    setup_avatar_view(mock_hass)

    mock_hass.http.register_view.assert_called_once()
    args = mock_hass.http.register_view.call_args[0]
    assert isinstance(args[0], SignalAvatarView)


def test_setup_avatar_view_without_http(mock_hass):
    """Test setting up avatar view without HTTP component (tests)."""
    mock_hass.http = None

    # Should not raise exception
    setup_avatar_view(mock_hass)


def test_token_expiration_time(mock_hass):
    """Test token expiration is approximately 1 hour."""
    current_time = time.time()
    _, expires = generate_avatar_token(mock_hass, "entry", "device")

    # Should expire in approximately 3600 seconds (1 hour)
    time_diff = expires - current_time
    assert 3599 <= time_diff <= 3601


def test_token_format_consistency(mock_hass):
    """Test that token format is consistent."""
    # Generate a token
    token, expires = generate_avatar_token(mock_hass, "entry", "device")

    # Both should have valid format: signature:timestamp
    assert ":" in token
    parts = token.split(":")
    assert len(parts) == 2
    assert len(parts[0]) == 16  # 16 char signature
    assert int(parts[1]) == expires  # Timestamp matches


def test_get_secret_creates_new_if_missing(mock_hass):
    """Test _get_secret creates a new secret if not available."""
    from custom_components.signal_gateway.avatar_view import _get_secret

    mock_hass.data = {}
    # Mock hasattr to return False for 'secret' attribute
    with patch("builtins.hasattr", return_value=False):
        secret = _get_secret(mock_hass)

        assert secret is not None
        assert len(secret) > 0
        assert "avatar_secret" in mock_hass.data


def test_get_secret_with_hass_data_secret(mock_hass):
    """Test _get_secret returns string from hass.data.get when hasattr returns True."""
    from custom_components.signal_gateway.avatar_view import _get_secret

    mock_data = MagicMock()
    mock_data.get.return_value = "secret_from_data"
    mock_hass.data = mock_data
    mock_hass.config.path.return_value = "fallback_path"

    secret = _get_secret(mock_hass)

    # Should call get with "secret" and fallback
    mock_data.get.assert_called_once()
    assert secret == "secret_from_data"
