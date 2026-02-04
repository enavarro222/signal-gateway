"""Service schema definitions for Signal Gateway notify."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.helpers import config_validation as cv

# Service registration schema
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("message"): cv.string,
        vol.Optional("title"): cv.string,
        vol.Optional("target"): vol.Any(cv.string, [cv.string]),
        vol.Optional("data"): vol.Schema(
            {
                vol.Optional("attachments"): [cv.string],
                vol.Optional("urls"): [cv.string],
                vol.Optional("verify_ssl"): cv.boolean,
                vol.Optional("text_mode"): vol.In(["normal", "styled"]),
            }
        ),
    }
)

# Service schema for GUI
GUI_SERVICE_SCHEMA = {
    "name": "Send message",
    "description": "Send a Signal message to one or more recipients",
    "fields": {
        "message": {
            "name": "Message",
            "description": "The message content to send",
            "required": True,
            "example": "Hello from Home Assistant!",
            "selector": {"text": {"multiline": True}},
        },
        "title": {
            "name": "Title",
            "description": "Optional title that will be prepended to the message",
            "required": False,
            "example": "Alert",
            "selector": {"text": {}},
        },
        "target": {
            "name": "Target",
            "description": (
                "Phone number (with country code) or group ID. "
                "Can be a single value or a list. If not provided, "
                "uses default recipients from configuration."
            ),
            "required": False,
            "example": "+1234567890",
            "selector": {"text": {}},
        },
        "data": {
            "name": "Data",
            "description": "Additional data for the notification",
            "required": False,
            "advanced": False,
            "selector": {
                "object": {
                    "options": {
                        "attachments": {
                            "name": "Attachments",
                            "description": "List of local file paths to attach",
                            "example": ["/config/www/camera_snapshot.jpg"],
                        },
                        "urls": {
                            "name": "URLs",
                            "description": "List of URLs to download and attach",
                            "example": ["https://example.com/image.jpg"],
                        },
                        "verify_ssl": {
                            "name": "Verify SSL",
                            "description": "Verify SSL certificates (default: true)",
                        },
                        "text_mode": {
                            "name": "Text Mode",
                            "description": (
                                "Format mode: 'normal' or 'styled' " "(default: normal)"
                            ),
                        },
                    }
                }
            },
        },
    },
}
