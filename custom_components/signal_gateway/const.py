"""Constants for the Signal Gateway integration."""

from typing import Final

DOMAIN: Final = "signal_gateway"
SERVICE_NOTIFY: Final = "send_message"
EVENT_SIGNAL_RECEIVED: Final = "signal_received"
EVENT_TYPING_INDICATOR: Final = "typing_indicator"

CONF_SIGNAL_CLI_REST_API_URL: Final = "signal_cli_rest_api_url"
CONF_PHONE_NUMBER: Final = "phone_number"
CONF_WEBSOCKET_ENABLED: Final = "websocket_enabled"
CONF_RECIPIENTS: Final = "recipients"
CONF_APPROVED_DEVICES: Final = "approved_devices"

ATTR_TARGET: Final = "target"
ATTR_MESSAGE: Final = "message"
ATTR_ATTACHMENTS: Final = "attachments"
