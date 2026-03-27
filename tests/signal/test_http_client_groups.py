"""Tests for Signal HTTP client groups API methods.

These tests validate that the implementation matches the signal-cli-rest-api swagger spec:
- GET /v1/groups/{number} - List all Signal Groups
- POST /v1/groups/{number} - Create a new Signal Group
- GET /v1/groups/{number}/{groupid} - List a Signal Group
- PUT /v1/groups/{number}/{groupid} - Update the state of a Signal Group
- DELETE /v1/groups/{number}/{groupid} - Delete a Signal Group
- POST /v1/groups/{number}/{groupid}/admins - Add admins
- DELETE /v1/groups/{number}/{groupid}/admins - Remove admins
- POST /v1/groups/{number}/{groupid}/members - Add members
- DELETE /v1/groups/{number}/{groupid}/members - Remove members
"""

import pytest
from aiohttp import ClientError
from unittest.mock import AsyncMock, MagicMock

from custom_components.signal_gateway.signal.models import SignalGroup


@pytest.mark.asyncio
async def test_list_groups_success(http_client, mock_response):
    """Test listing groups successfully (matches swagger: GET /v1/groups/{number})."""
    json_data = [
        {
            "id": "group.abc123",
            "name": "Family",
            "internal_id": "internal123",
            "members": ["+1111", "+2222"],
            "admins": ["+1111"],
            "description": "Family group",
            "blocked": False,
        },
        {
            "id": "group.def456",
            "name": "Work",
            "internal_id": "internal456",
            "members": ["+3333"],
            "admins": ["+3333"],
        },
    ]
    response = mock_response(json_data=json_data)
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.list_groups()

    assert len(result) == 2
    assert isinstance(result[0], SignalGroup)
    assert result[0].id == "group.abc123"
    assert result[0].name == "Family"
    assert result[0].member_count == 2
    assert result[1].name == "Work"
    http_client.session.get.assert_called_once()


@pytest.mark.asyncio
async def test_list_groups_error(http_client, mock_response):
    """Test listing groups with API error."""
    response = mock_response(side_effect=ClientError("Connection failed"))
    http_client.session.get = MagicMock(return_value=response)

    with pytest.raises(ClientError):
        await http_client.list_groups()


@pytest.mark.asyncio
async def test_get_group_success(http_client, mock_response):
    """Test getting a specific group (matches swagger: GET /v1/groups/{number}/{groupid})."""
    json_data = {
        "id": "group.abc123",
        "name": "Family",
        "internal_id": "internal123",
        "members": ["+1111", "+2222", "+3333"],
        "admins": ["+1111"],
        "description": "My family",
        "invite_link": "https://signal.group/...",
    }
    response = mock_response(json_data=json_data)
    http_client.session.get = MagicMock(return_value=response)

    result = await http_client.get_group("group.abc123")

    assert isinstance(result, SignalGroup)
    assert result.id == "group.abc123"
    assert result.name == "Family"
    assert result.member_count == 3
    assert result.invite_link == "https://signal.group/..."
    http_client.session.get.assert_called_once()


@pytest.mark.asyncio
async def test_create_group_success(http_client, mock_response):
    """Test creating a new group (matches swagger: POST /v1/groups/{number})."""
    response = mock_response(json_data={"id": "group.new123"})
    http_client.session.post = MagicMock(return_value=response)

    result = await http_client.create_group(
        name="Test Group",
        members=["+1111", "+2222"],
        description="A test group",
        group_link="enabled",
    )

    assert result == "group.new123"
    http_client.session.post.assert_called_once()
    call_args = http_client.session.post.call_args
    assert call_args[0][0] == "http://localhost:8080/v1/groups/+33612345678"
    assert call_args[1]["json"]["name"] == "Test Group"
    assert call_args[1]["json"]["members"] == ["+1111", "+2222"]
    assert call_args[1]["json"]["description"] == "A test group"
    assert call_args[1]["json"]["group_link"] == "enabled"


@pytest.mark.asyncio
async def test_create_group_minimal(http_client, mock_response):
    """Test creating a group with minimal parameters."""
    response = mock_response(json_data={"id": "group.minimal"})
    http_client.session.post = MagicMock(return_value=response)

    result = await http_client.create_group(name="Simple", members=["+1111"])

    assert result == "group.minimal"
    call_args = http_client.session.post.call_args
    payload = call_args[1]["json"]
    assert payload["name"] == "Simple"
    assert payload["members"] == ["+1111"]
    assert "description" not in payload
    assert payload["group_link"] == "disabled"


@pytest.mark.asyncio
async def test_update_group_success(http_client, mock_response):
    """Test updating a group (matches swagger: PUT /v1/groups/{number}/{groupid})."""
    response = mock_response()
    http_client.session.put = MagicMock(return_value=response)

    await http_client.update_group(
        group_id="group.abc123",
        name="Updated Name",
        description="New description",
    )

    http_client.session.put.assert_called_once()
    call_args = http_client.session.put.call_args
    assert (
        call_args[0][0] == "http://localhost:8080/v1/groups/+33612345678/group.abc123"
    )
    assert call_args[1]["json"]["name"] == "Updated Name"
    assert call_args[1]["json"]["description"] == "New description"


@pytest.mark.asyncio
async def test_update_group_no_changes(http_client):
    """Test updating a group with no parameters (should return early)."""
    http_client.session.put = AsyncMock()

    await http_client.update_group(group_id="group.abc123")

    http_client.session.put.assert_not_called()


@pytest.mark.asyncio
async def test_delete_group_success(http_client, mock_response):
    """Test deleting a group (matches swagger: DELETE /v1/groups/{number}/{groupid})."""
    response = mock_response()
    http_client.session.delete = MagicMock(return_value=response)

    await http_client.delete_group("group.abc123")

    http_client.session.delete.assert_called_once()


@pytest.mark.asyncio
async def test_add_group_members_success(http_client, mock_response):
    """Test adding members to a group (matches swagger: POST /v1/groups/{number}/{groupid}/members)."""
    response = mock_response()
    http_client.session.post = MagicMock(return_value=response)

    await http_client.add_group_members("group.abc123", ["+4444", "+5555"])

    http_client.session.post.assert_called_once()
    call_args = http_client.session.post.call_args
    assert (
        call_args[0][0]
        == "http://localhost:8080/v1/groups/+33612345678/group.abc123/members"
    )
    assert call_args[1]["json"]["members"] == ["+4444", "+5555"]


@pytest.mark.asyncio
async def test_remove_group_members_success(http_client, mock_response):
    """Test removing members from a group (matches swagger: DELETE /v1/groups/{number}/{groupid}/members)."""
    response = mock_response()
    http_client.session.delete = MagicMock(return_value=response)

    await http_client.remove_group_members("group.abc123", ["+2222"])

    http_client.session.delete.assert_called_once()
    call_args = http_client.session.delete.call_args
    assert (
        call_args[0][0]
        == "http://localhost:8080/v1/groups/+33612345678/group.abc123/members"
    )
    assert call_args[1]["json"]["members"] == ["+2222"]


@pytest.mark.asyncio
async def test_add_group_admins_success(http_client, mock_response):
    """Test adding admins to a group (matches swagger: POST /v1/groups/{number}/{groupid}/admins)."""
    response = mock_response()
    http_client.session.post = MagicMock(return_value=response)

    await http_client.add_group_admins("group.abc123", ["+3333"])

    http_client.session.post.assert_called_once()
    call_args = http_client.session.post.call_args
    assert (
        call_args[0][0]
        == "http://localhost:8080/v1/groups/+33612345678/group.abc123/admins"
    )
    assert call_args[1]["json"]["admins"] == ["+3333"]


@pytest.mark.asyncio
async def test_remove_group_admins_success(http_client, mock_response):
    """Test removing admins from a group (matches swagger: DELETE /v1/groups/{number}/{groupid}/admins)."""
    response = mock_response()
    http_client.session.delete = MagicMock(return_value=response)

    await http_client.remove_group_admins("group.abc123", ["+1111"])

    http_client.session.delete.assert_called_once()
    call_args = http_client.session.delete.call_args
    assert (
        call_args[0][0]
        == "http://localhost:8080/v1/groups/+33612345678/group.abc123/admins"
    )
    assert call_args[1]["json"]["admins"] == ["+1111"]
