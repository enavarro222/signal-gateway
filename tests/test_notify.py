import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.signal_gateway.notify import async_setup_entry


@pytest.mark.asyncio
async def test_notify_async_setup_entry_success():
    hass = MagicMock()
    entry = MagicMock()
    async_add_entities = MagicMock()
    # Simuler la présence du client dans hass.data
    hass.data = {
        "signal_gateway": {
            entry.entry_id: {"client": object(), "service_name": "test_service"}
        }
    }
    result = await async_setup_entry(hass, entry, async_add_entities)
    assert result is True


@pytest.mark.asyncio
async def test_notify_async_setup_entry_no_client():
    hass = MagicMock()
    entry = MagicMock()
    async_add_entities = MagicMock()
    # Simuler l'absence du client
    hass.data = {"signal_gateway": {entry.entry_id: {}}}
    result = await async_setup_entry(hass, entry, async_add_entities)
    assert result is False
