import json
from unittest.mock import AsyncMock
import pytest
import asyncio

from custom_components.signal_gateway.signal.websocket_listener import (
    SignalWebSocketListener,
)

from .conftest import MockWebSocketClient


@pytest.mark.asyncio
async def test__connect_and_listen_running_becomes_false(
    mock_websocket_connects, mock_session
):
    """
    Teste que la boucle s'arrête si _running devient False pendant la réception.
    """
    messages = [json.dumps({"data": "msg1"}), json.dumps({"data": "msg2"})]

    # configure the websocket mock
    async def websockets_clients_generator(*args, **kwargs):
        async def websocket_messages_generator():
            for msg in messages:
                yield msg

        yield MockWebSocketClient(websocket_messages_generator)

    mock_websocket_connects.set_clients_generator(websockets_clients_generator)

    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="123", session=mock_session
    )
    listener._running = True

    # On modifie le handler pour mettre _running à False après le premier appel
    handler = AsyncMock()

    async def handler_and_stop(msg):
        listener._running = False
        await handler(msg)

    listener.set_message_handler(handler_and_stop)

    await listener._connect_and_listen("ws://fake")
    # Le handler ne doit être appelé qu'une seule fois (le second message ne doit pas être traité)
    handler.assert_awaited_once()


@pytest.mark.asyncio
async def test__connect_and_listen_cancel_error(mock_websocket_connects, mock_session):
    """
    Teste que la boucle s'arrête si _running devient False pendant la réception.
    """
    messages = [json.dumps({"data": "msg1"}), json.dumps({"data": "msg2"})]

    # configure the websocket mock
    async def websockets_clients_generator(*args, **kwargs):
        async def websocket_messages_generator():
            for msg in messages:
                yield msg
                raise asyncio.CancelledError()

        yield MockWebSocketClient(websocket_messages_generator)

    mock_websocket_connects.set_clients_generator(websockets_clients_generator)

    listener = SignalWebSocketListener(
        api_url="http://localhost:8080", phone_number="123", session=mock_session
    )
    listener._running = True

    # On modifie le handler pour mettre _running à False après le premier appel
    handler = AsyncMock()
    listener.set_message_handler(handler)

    await listener._connect_and_listen("ws://fake")
    # Le handler ne doit être appelé qu'une seule fois (le second message ne doit pas être traité)
    handler.assert_awaited_once()
