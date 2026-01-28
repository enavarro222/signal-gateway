"""Constants for the Signal Gateway integration."""

from typing import Final

DOMAIN: Final = "signal_gateway"
SERVICE_NOTIFY: Final = "send_message"
EVENT_SIGNAL_RECEIVED: Final = "signal_received"

CONF_SIGNAL_CLI_REST_API_URL: Final = "signal_cli_rest_api_url"
CONF_PHONE_NUMBER: Final = "phone_number"
CONF_WEBSOCKET_ENABLED: Final = "websocket_enabled"
CONF_RECIPIENTS: Final = "recipients"

ATTR_TARGET: Final = "target"
ATTR_MESSAGE: Final = "message"
ATTR_ATTACHMENTS: Final = "attachments"
