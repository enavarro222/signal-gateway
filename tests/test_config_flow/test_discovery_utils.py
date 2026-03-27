"""Tests for device discovery module."""

from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import pytest

from custom_components.signal_gateway.config_flow.discovery import discover_devices
from custom_components.signal_gateway.signal.models import SignalContact, SignalGroup


@pytest.mark.asyncio
async def test_discover_devices_with_contacts_and_groups(
    mock_hass, mock_session, mock_contacts, mock_groups
):
    """Test discover_devices returns both contacts and groups."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_instance.list_groups = AsyncMock(return_value=mock_groups)
        mock_client.return_value = mock_instance

        devices = await discover_devices(
            mock_hass,
            "http://localhost:8080",
            "+1111111111",
            mock_session,
        )

        # Should have 2 contacts + 1 group
        assert len(devices) == 3
        assert "contact_+1234567890" in devices
        assert devices["contact_+1234567890"] == "John Doe"
        assert "contact_+9876543210" in devices
        assert devices["contact_+9876543210"] == "Jane Smith"
        assert "group_group123" in devices
        assert devices["group_group123"] == "Family"


@pytest.mark.asyncio
async def test_discover_devices_contact_without_name(mock_hass, mock_session):
    """Test discover_devices handles contacts without names."""
    contact = SignalContact(
        number="+5555555555",
        uuid="uuid-3",
        name="",
        given_name="",
        profile_name="",
        username=None,
        nickname=None,
        profile=None,
        note="",
        color="red",
        message_expiration="0",
        blocked=False,
    )

    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=[contact])
        mock_instance.list_groups = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        devices = await discover_devices(
            mock_hass, "http://localhost:8080", "+1111111111", mock_session
        )

        assert len(devices) == 1
        assert "contact_+5555555555" in devices
        # Should fall back to number only
        assert devices["contact_+5555555555"] == "+5555555555"


@pytest.mark.asyncio
async def test_discover_devices_only_contacts(mock_hass, mock_session, mock_contacts):
    """Test discover_devices with only contacts (no groups)."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_instance.list_groups = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        devices = await discover_devices(
            mock_hass, "http://localhost:8080", "+1111111111", mock_session
        )

        assert len(devices) == 2
        assert all(k.startswith("contact_") for k in devices.keys())


@pytest.mark.asyncio
async def test_discover_devices_only_groups(mock_hass, mock_session, mock_groups):
    """Test discover_devices with only groups (no contacts)."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=[])
        mock_instance.list_groups = AsyncMock(return_value=mock_groups)
        mock_client.return_value = mock_instance

        devices = await discover_devices(
            mock_hass, "http://localhost:8080", "+1111111111", mock_session
        )

        assert len(devices) == 1
        assert all(k.startswith("group_") for k in devices.keys())


@pytest.mark.asyncio
async def test_discover_devices_empty(mock_hass, mock_session):
    """Test discover_devices with no contacts or groups."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=[])
        mock_instance.list_groups = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        devices = await discover_devices(
            mock_hass, "http://localhost:8080", "+1111111111", mock_session
        )

        assert devices == {}


@pytest.mark.asyncio
async def test_discover_devices_connection_error(mock_hass, mock_session):
    """Test discover_devices raises DiscoveryError on connection failure."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )
        mock_client.return_value = mock_instance

        with pytest.raises(aiohttp.ClientError):
            await discover_devices(
                mock_hass, "http://localhost:8080", "+1111111111", mock_session
            )


@pytest.mark.asyncio
async def test_discover_devices_api_error(mock_hass, mock_session):
    """Test discover_devices handles API errors."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(side_effect=Exception("API error"))
        mock_client.return_value = mock_instance

        with pytest.raises(Exception):
            await discover_devices(
                mock_hass, "http://localhost:8080", "+1111111111", mock_session
            )


@pytest.mark.asyncio
async def test_discover_devices_partial_failure(mock_hass, mock_session, mock_contacts):
    """Test discover_devices when groups fail but contacts succeed."""
    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=mock_contacts)
        mock_instance.list_groups = AsyncMock(
            side_effect=Exception("Groups API failed")
        )
        mock_client.return_value = mock_instance

        # Should propagate the exception
        with pytest.raises(Exception, match="Groups API failed"):
            await discover_devices(
                mock_hass, "http://localhost:8080", "+1111111111", mock_session
            )


@pytest.mark.asyncio
async def test_discover_devices_duplicate_names(mock_hass, mock_session):
    """Test discover_devices handles duplicate names correctly."""
    contacts = [
        SignalContact(
            number="+1111111111",
            uuid="uuid-1",
            name="John Doe",
            given_name="John",
            profile_name="John",
            username=None,
            nickname=None,
            profile=None,
            note="",
            color="blue",
            message_expiration="0",
            blocked=False,
        ),
        SignalContact(
            number="+2222222222",
            uuid="uuid-2",
            name="John Doe",  # Same name
            given_name="John",
            profile_name="John",
            username=None,
            nickname=None,
            profile=None,
            note="",
            color="green",
            message_expiration="0",
            blocked=False,
        ),
    ]

    with patch(
        "custom_components.signal_gateway.config_flow.discovery.SignalClient"
    ) as mock_client:
        mock_instance = AsyncMock()
        mock_instance.list_contacts = AsyncMock(return_value=contacts)
        mock_instance.list_groups = AsyncMock(return_value=[])
        mock_client.return_value = mock_instance

        devices = await discover_devices(
            mock_hass, "http://localhost:8080", "+1111111111", mock_session
        )

        # Both should be present with different IDs
        assert len(devices) == 2
        assert "contact_+1111111111" in devices
        assert "contact_+2222222222" in devices
        # Display names can be the same - IDs differentiate them
        assert devices["contact_+1111111111"] == "John Doe"
        assert devices["contact_+2222222222"] == "John Doe"
