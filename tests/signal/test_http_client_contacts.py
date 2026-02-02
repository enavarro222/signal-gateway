"""Tests for Signal HTTP client contacts API methods.

These tests validate that the implementation matches the signal-cli-rest-api swagger spec:
- GET /v1/contacts/{number} - List Contacts (returns array of ListContactsResponse)
- GET /v1/contacts/{number}/{uuid} - List Contact (returns single ListContactsResponse)
- PUT /v1/contacts/{number} - Updates contact info (uses UpdateContactRequest)
"""

import pytest
from aiohttp import ClientError
from unittest.mock import MagicMock

from custom_components.signal_gateway.signal.models import SignalContact


@pytest.mark.asyncio
async def test_list_contacts_success(http_client, mock_response):
    """Test listing contacts successfully (matches swagger: GET /v1/contacts/{number})."""
    json_data = [
        {
            "number": "+1234567890",
            "uuid": "uuid-1234",
            "name": "John Doe",
            "profile_name": "John",
            "username": "johndoe.123",
            "profile": {
                "about": "Available",
                "has_avatar": True,
            },
            "blocked": False,
        },
        {
            "number": "+9876543210",
            "uuid": "uuid-5678",
            "given_name": "Jane",
            "profile_name": "Jane Smith",
        },
    ]
    response = mock_response(json_data=json_data)
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.list_contacts()

    assert len(result) == 2
    assert isinstance(result[0], SignalContact)
    assert result[0].number == "+1234567890"
    assert result[0].name == "John Doe"
    assert result[0].username == "johndoe.123"
    assert result[0].display_name == "John Doe"
    assert result[0].profile.about == "Available"
    assert result[0].profile.has_avatar is True
    assert result[1].display_name == "Jane Smith"
    http_client.session.get.assert_called_once()


@pytest.mark.asyncio
async def test_list_contacts_empty(http_client, mock_response):
    """Test listing contacts when none exist."""
    response = mock_response(json_data=[])
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.list_contacts()

    assert result == []


@pytest.mark.asyncio
async def test_list_contacts_error(http_client, mock_response):
    """Test listing contacts with API error."""
    response = mock_response(side_effect=ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(ClientError):
        await http_client.list_contacts()


@pytest.mark.asyncio
async def test_get_contact_success(http_client, mock_response):
    """Test getting a specific contact (matches swagger: GET /v1/contacts/{number}/{uuid})."""
    json_data = {
        "number": "+1234567890",
        "uuid": "uuid-1234",
        "name": "John Doe",
        "profile_name": "John",
        "given_name": "John",
        "username": "johndoe.123",
        "profile": {
            "about": "Hello world",
            "given_name": "John",
            "lastname": "Doe",
            "has_avatar": True,
            "last_updated_timestamp": 1234567890,
        },
        "nickname": {
            "name": "Johnny",
            "given_name": "John",
            "family_name": "Doe",
        },
        "note": "Friend from work",
        "color": "#FF5733",
        "blocked": False,
    }
    response = mock_response(json_data=json_data)
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.get_contact("uuid-1234")

    assert isinstance(result, SignalContact)
    assert result.number == "+1234567890"
    assert result.uuid == "uuid-1234"
    assert result.display_name == "John Doe"
    assert result.nickname.name == "Johnny"
    assert result.profile.about == "Hello world"
    assert result.note == "Friend from work"
    assert result.color == "#FF5733"
    http_client.session.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_contact_minimal_data(http_client, mock_response):
    """Test getting a contact with minimal data."""
    json_data = {
        "number": "+9999999999",
        "uuid": "uuid-minimal",
    }
    response = mock_response(json_data=json_data)
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.get_contact("uuid-minimal")

    assert result.number == "+9999999999"
    assert result.uuid == "uuid-minimal"
    assert result.display_name == "+9999999999"  # Falls back to number
    assert result.nickname.name == ""
    assert result.profile.about == ""


@pytest.mark.asyncio
async def test_update_contact_with_name(http_client, mock_response):
    """Test updating a contact with name (matches swagger: PUT /v1/contacts/{number})."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    await http_client.update_contact(
        recipient="+1234567890",
        name="John Updated",
    )

    http_client.session.put.assert_called_once()
    call_args = http_client.session.put.call_args
    assert call_args[0][0] == "http://localhost:8080/v1/contacts/+33612345678"
    assert call_args[1]["json"]["recipient"] == "+1234567890"
    assert call_args[1]["json"]["name"] == "John Updated"
    assert "expiration_in_seconds" not in call_args[1]["json"]


@pytest.mark.asyncio
async def test_update_contact_with_expiration(http_client, mock_response):
    """Test updating a contact with message expiration."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    await http_client.update_contact(
        recipient="+1234567890",
        name="John",
        expiration_in_seconds=3600,
    )

    call_args = http_client.session.put.call_args
    payload = call_args[1]["json"]
    assert payload["recipient"] == "+1234567890"
    assert payload["name"] == "John"
    assert payload["expiration_in_seconds"] == 3600


@pytest.mark.asyncio
async def test_update_contact_minimal(http_client, mock_response):
    """Test updating a contact with only recipient (add without name)."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    await http_client.update_contact(recipient="+1234567890")

    call_args = http_client.session.put.call_args
    payload = call_args[1]["json"]
    assert payload["recipient"] == "+1234567890"
    assert "name" not in payload
    assert "expiration_in_seconds" not in payload


@pytest.mark.asyncio
async def test_update_contact_error(http_client, mock_response):
    """Test updating a contact with API error."""
    response = mock_response(side_effect=ClientError("API error"))
    http_client.session.put = MagicMock(return_value=response)

    with pytest.raises(ClientError):
        await http_client.update_contact("+1234567890", "John")
