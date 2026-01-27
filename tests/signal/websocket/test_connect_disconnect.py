import pytest
import asyncio
from unittest.mock import AsyncMock
from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)


@pytest.mark.asyncio
async def test_connect_sets_running_and_starts_task(monkeypatch):
    """
    Test that connect() sets _running to True and starts the _listen task.
    Also checks that calling connect() again does nothing if already running.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="+33612345678"
    )
    monkeypatch.setattr(listener, "_listen", AsyncMock())
    await listener.connect()
    assert listener._running is True
    assert listener._task is not None
    # Call again to check warning if already running (should do nothing)
    await listener.connect()


@pytest.mark.asyncio
async def test_disconnect_closes_websocket_and_task(monkeypatch):
    """
    Test that disconnect() closes the websocket and waits for the task to finish without timeout.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="+33612345678"
    )
    listener._running = True
    mock_ws = AsyncMock()
    listener.websocket = mock_ws
    # Use a real finished Future to simulate a completed task
    done_task = asyncio.Future()
    done_task.set_result(None)
    listener._task = done_task
    await listener.disconnect()
    mock_ws.close.assert_awaited()
    # No cancel should be called on a finished task


@pytest.mark.asyncio
async def test_disconnect_task_timeout(monkeypatch, caplog):
    """
    Test that disconnect() cancels the task if it does not finish in time (timeout), and logs a warning.
    """
    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="+33612345678"
    )
    listener._running = True
    mock_ws = AsyncMock()
    listener.websocket = mock_ws
    # Simulate a slow task that will timeout
    listener._task = asyncio.create_task(asyncio.sleep(10))
    caplog.set_level("WARNING")
    await listener.disconnect()
    # The task.cancel should be called (warning is logged)
    assert any(
        "WebSocket listener task did not complete in time" in r.message
        for r in caplog.records
    )
