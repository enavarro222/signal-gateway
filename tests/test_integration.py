"""Basic import a loading tests for Signal Gateway integration."""


def test_imports():
    from custom_components.signal_gateway import async_setup_entry, async_unload_entry
    from custom_components.signal_gateway.const import DOMAIN, SERVICE_NOTIFY
    from custom_components.signal_gateway.config_flow import SignalGatewayConfigFlow
    from custom_components.signal_gateway.signal import (
        SignalClient,
        SignalWebSocketListener,
    )

    assert DOMAIN == "signal_gateway"
    assert SERVICE_NOTIFY == "send_message"


def test_constants():
    from custom_components.signal_gateway.const import (
        DOMAIN,
        SERVICE_NOTIFY,
        EVENT_SIGNAL_RECEIVED,
        CONF_SIGNAL_CLI_REST_API_URL,
        CONF_PHONE_NUMBER,
        CONF_WEBSOCKET_ENABLED,
    )

    assert isinstance(DOMAIN, str)
    assert isinstance(SERVICE_NOTIFY, str)
    assert isinstance(EVENT_SIGNAL_RECEIVED, str)
    assert isinstance(CONF_SIGNAL_CLI_REST_API_URL, str)
    assert isinstance(CONF_PHONE_NUMBER, str)
    assert isinstance(CONF_WEBSOCKET_ENABLED, str)


def test_config_flow_initialization():
    from custom_components.signal_gateway.config_flow import SignalGatewayConfigFlow

    config_flow = SignalGatewayConfigFlow()
    assert config_flow.VERSION == 1
