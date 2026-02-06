"""Tests for http_client error handling and edge cases."""

import json
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.signal_gateway.signal.http_client import SignalHTTPClient


@pytest.mark.asyncio
async def test_send_message_api_error(http_client, mock_response):
    """Test send_message handles API errors."""
    response = mock_response(status=500)
    response.text = AsyncMock(return_value="Internal Server Error")
    http_client.session.post = MagicMock(return_value=response)

    with pytest.raises(RuntimeError, match="Signal API error: 500"):
        await http_client.send_message("+33698765432", "Hello")


@pytest.mark.asyncio
async def test_send_message_with_attachments(http_client, mock_response):
    """Test send_message with base64 attachments."""
    response = mock_response(json_data={"result": "ok"})
    http_client.session.post = MagicMock(return_value=response)

    attachments = ["base64encodeddata1", "base64encodeddata2"]
    result = await http_client.send_message(
        "+33698765432", "Hello", base64_attachments=attachments
    )

    # Verify attachments were included
    call_args = http_client.session.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["base64_attachments"] == attachments
    assert result == {"result": "ok"}


@pytest.mark.asyncio
async def test_send_message_non_json_response(http_client, mock_response):
    """Test send_message handles non-JSON responses."""
    response = mock_response()
    response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(None, None))
    response.text = AsyncMock(return_value="OK - message sent")
    http_client.session.post = MagicMock(return_value=response)

    result = await http_client.send_message("+33698765432", "Hello")
    assert result == {"success": True, "response": "OK - message sent"}


@pytest.mark.asyncio
async def test_send_message_json_decode_error(http_client, mock_response):
    """Test send_message handles JSON decode errors."""
    response = mock_response()
    response.text = AsyncMock(return_value="Invalid JSON {")
    response.json = AsyncMock(side_effect=json.JSONDecodeError("", "", 0))
    http_client.session.post = MagicMock(return_value=response)

    result = await http_client.send_message("+33698765432", "Hello")
    assert result == {"success": True, "response": "Invalid JSON {"}


@pytest.mark.asyncio
async def test_send_message_client_error(http_client, mock_response):
    """Test send_message handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.post = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.send_message("+33698765432", "Hello")


@pytest.mark.asyncio
async def test_api_url_trailing_slash_stripped(http_client):
    """Test that trailing slash is stripped from API URL."""
    client = SignalHTTPClient(
        api_url="http://localhost:8080/",
        phone_number="+33612345678",
        session=http_client.session,
    )
    assert client.api_url == "http://localhost:8080"


@pytest.mark.asyncio
async def test_list_groups_client_error(http_client, mock_response):
    """Test list_groups handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.list_groups()


@pytest.mark.asyncio
async def test_get_group_client_error(http_client, mock_response):
    """Test get_group handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.get_group("group123")


@pytest.mark.asyncio
async def test_create_group_client_error(http_client, mock_response):
    """Test create_group handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.post = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.create_group("Test Group", ["+1234567890"])


@pytest.mark.asyncio
async def test_update_group_client_error(http_client, mock_response):
    """Test update_group handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.put = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.update_group("group123", name="New Name")


@pytest.mark.asyncio
async def test_delete_group_client_error(http_client, mock_response):
    """Test delete_group handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.delete = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.delete_group("group123")


@pytest.mark.asyncio
async def test_add_group_members_client_error(http_client, mock_response):
    """Test add_group_members handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.post = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.add_group_members("group123", ["+1234567890"])


@pytest.mark.asyncio
async def test_remove_group_members_client_error(http_client, mock_response):
    """Test remove_group_members handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.delete = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.remove_group_members("group123", ["+1234567890"])


@pytest.mark.asyncio
async def test_add_group_admins_client_error(http_client, mock_response):
    """Test add_group_admins handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.post = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.add_group_admins("group123", ["+1234567890"])


@pytest.mark.asyncio
async def test_remove_group_admins_client_error(http_client, mock_response):
    """Test remove_group_admins handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.delete = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.remove_group_admins("group123", ["+1234567890"])


@pytest.mark.asyncio
async def test_list_contacts_client_error(http_client, mock_response):
    """Test list_contacts handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.list_contacts()


@pytest.mark.asyncio
async def test_get_contact_client_error(http_client, mock_response):
    """Test get_contact handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.get_contact("uuid-123")


@pytest.mark.asyncio
async def test_update_contact_client_error(http_client, mock_response):
    """Test update_contact handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.put = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.update_contact("+1234567890", name="John Doe")


@pytest.mark.asyncio
async def test_update_contact_with_expiration(http_client, mock_response):
    """Test update_contact with expiration time."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    await http_client.update_contact(
        "+1234567890", name="John Doe", expiration_in_seconds=3600
    )

    # Verify payload includes expiration
    call_args = http_client.session.put.call_args
    payload = call_args.kwargs["json"]
    assert payload["recipient"] == "+1234567890"
    assert payload["name"] == "John Doe"
    assert payload["expiration_in_seconds"] == 3600


@pytest.mark.asyncio
async def test_update_contact_minimal(http_client, mock_response):
    """Test update_contact with minimal parameters."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    await http_client.update_contact("+1234567890")

    # Verify payload only includes recipient
    call_args = http_client.session.put.call_args
    payload = call_args.kwargs["json"]
    assert payload["recipient"] == "+1234567890"
    assert "name" not in payload
    assert "expiration_in_seconds" not in payload


@pytest.mark.asyncio
async def test_get_contact_avatar_client_error(http_client, mock_response):
    """Test get_contact_avatar handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.get_contact_avatar("uuid-123")


@pytest.mark.asyncio
async def test_get_contact_avatar_success(http_client, mock_response):
    """Test get_contact_avatar returns avatar bytes."""
    avatar_data = b"\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR"  # Fake PNG header

    response = mock_response()
    response.read = AsyncMock(return_value=avatar_data)
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.get_contact_avatar("uuid-123")
    assert result == avatar_data


@pytest.mark.asyncio
async def test_get_group_avatar_client_error(http_client, mock_response):
    """Test get_group_avatar handles ClientError exceptions."""
    response = mock_response(side_effect=aiohttp.ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(aiohttp.ClientError, match="Connection failed"):
        await http_client.get_group_avatar("group123")


@pytest.mark.asyncio
async def test_get_group_avatar_success(http_client, mock_response):
    """Test get_group_avatar returns avatar bytes."""
    avatar_data = b"\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR"  # Fake PNG header

    response = mock_response()
    response.read = AsyncMock(return_value=avatar_data)
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.get_group_avatar("group123")
    assert result == avatar_data


@pytest.mark.asyncio
async def test_update_group_no_updates(http_client):
    """Test update_group with no parameters returns early."""
    # Should return without making any API call
    await http_client.update_group("group123")

    # Verify no API call was made
    assert not http_client.session.put.called


@pytest.mark.asyncio
async def test_create_group_with_permissions(http_client, mock_response):
    """Test create_group with permissions parameter."""
    response = mock_response(json_data={"id": "group.new123"})
    http_client.session.post = MagicMock(return_value=response)

    permissions = {"addMembers": "every-member", "editDetails": "only-admins"}
    result = await http_client.create_group(
        name="Test Group", members=["+1234567890"], permissions=permissions
    )

    assert result == "group.new123"
    call_args = http_client.session.post.call_args
    payload = call_args.kwargs["json"]
    assert payload["permissions"] == permissions


@pytest.mark.asyncio
async def test_update_group_with_permissions(http_client, mock_response):
    """Test update_group with permissions parameter."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    permissions = {"addMembers": "every-member"}
    await http_client.update_group("group123", permissions=permissions)

    call_args = http_client.session.put.call_args
    payload = call_args.kwargs["json"]
    assert payload["permissions"] == permissions


@pytest.mark.asyncio
async def test_update_group_with_group_link(http_client, mock_response):
    """Test update_group with group_link parameter."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    await http_client.update_group("group123", group_link="enabled-with-approval")

    call_args = http_client.session.put.call_args
    payload = call_args.kwargs["json"]
    assert payload["group_link"] == "enabled-with-approval"
