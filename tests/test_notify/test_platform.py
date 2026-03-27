import pytest
from custom_components.signal_gateway.notify import async_setup_entry


@pytest.mark.asyncio
async def test_notify_async_setup_entry_success(
    mock_hass, mock_entry, mock_add_entities, mock_signal_client
):
    """Test successful platform setup."""
    from custom_components.signal_gateway.const import DOMAIN

    # Setup data
    mock_hass.data[DOMAIN][mock_entry.entry_id] = {
        "client": mock_signal_client,
        "service_name": "test_service",
    }

    result = await async_setup_entry(mock_hass, mock_entry, mock_add_entities)
    assert result is True


@pytest.mark.asyncio
async def test_notify_async_setup_entry_no_client(
    mock_hass, mock_entry, mock_add_entities
):
    """Test setup when client is missing."""
    from custom_components.signal_gateway.const import DOMAIN

    mock_hass.data[DOMAIN][mock_entry.entry_id] = {}
    result = await async_setup_entry(mock_hass, mock_entry, mock_add_entities)
    assert result is False
