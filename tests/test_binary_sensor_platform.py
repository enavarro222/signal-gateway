"""Tests for Signal Gateway binary_sensor platform setup."""

from unittest.mock import MagicMock

import pytest

from custom_components.signal_gateway.binary_sensor import async_setup_entry
from custom_components.signal_gateway.data import SignalGatewayEntryData
from custom_components.signal_gateway.const import DOMAIN


@pytest.fixture
def mock_hass_binary_sensor(mock_hass, mock_signal_client, mock_entry, mock_contact_coordinator, mock_group_coordinator, sample_contact, sample_group):
    """Create a mock Home Assistant instance configured for binary_sensor tests."""
    mock_hass.data[DOMAIN][mock_entry.entry_id] = SignalGatewayEntryData(
        client=mock_signal_client,
        service_name="test_signal",
        default_recipients=[],
        coordinators={
            f"contact_{sample_contact.uuid}": mock_contact_coordinator,
            f"group_{sample_group.internal_id}": mock_group_coordinator,
        },
    )
    return mock_hass


async def test_async_setup_entry_with_contacts_and_groups(
    mock_hass_binary_sensor,
    mock_entry,
    mock_signal_client,
    sample_contact,
    sample_group,
):
    """Test binary_sensor platform setup with contacts and groups."""
    mock_signal_client.list_contacts.return_value = [sample_contact]
    mock_signal_client.list_groups.return_value = [sample_group]

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass_binary_sensor, mock_entry, async_add_entities)

    # Verify contacts and groups were fetched
    mock_signal_client.list_contacts.assert_called_once()
    mock_signal_client.list_groups.assert_called_once()

    # Verify 2 binary_sensor entities were created (1 contact + 1 group)
    assert async_add_entities.call_count == 1
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 2


async def test_async_setup_entry_no_contacts_or_groups(
    mock_hass_binary_sensor, mock_entry, mock_signal_client
):
    """Test binary_sensor platform setup with no contacts or groups."""
    mock_signal_client.list_contacts.return_value = []
    mock_signal_client.list_groups.return_value = []

    async_add_entities = MagicMock()

    await async_setup_entry(mock_hass_binary_sensor, mock_entry, async_add_entities)

    # Verify entities were added (empty list)
    assert async_add_entities.call_count == 1
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 0


async def test_async_setup_entry_api_error(
    mock_hass_binary_sensor, mock_entry, mock_signal_client
):
    """Test binary_sensor platform setup when API calls fail."""
    mock_signal_client.list_contacts.side_effect = Exception("API error")

    async_add_entities = MagicMock()

    # Setup should raise the exception - HA will retry automatically
    with pytest.raises(Exception, match="API error"):
        await async_setup_entry(mock_hass_binary_sensor, mock_entry, async_add_entities)

    # async_add_entities should not be called when setup fails
    assert async_add_entities.call_count == 0
