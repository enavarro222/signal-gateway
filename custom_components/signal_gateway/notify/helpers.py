"""Helper functions for notify service."""

from __future__ import annotations

import logging
from typing import Optional, Union

_LOGGER = logging.getLogger(__name__)


def fix_phone_number(recipient: str) -> str:
    """Fix phone number format by ensuring it has a '+' prefix.

    Home Assistant may interpret phone numbers as integers in certain contexts,
    which strips the leading '+' sign. This function restores the '+' prefix
    for phone numbers that are all digits but missing it.

    Args:
        recipient: The phone number to fix, with or without '+' prefix.

    Returns:
        The phone number with '+' prefix added if it was missing.

    Examples:
        >>> fix_phone_number("+1234567890")
        '+1234567890'
        >>> fix_phone_number("1234567890")
        '+1234567890'
        >>> fix_phone_number("+44123456")
        '+44123456'
        >>> fix_phone_number("notanumber")
        'notanumber'
    """
    if not recipient.startswith("+") and recipient.isdigit():
        recipient = f"+{recipient}"
    return recipient


def normalize_targets(
    target: Optional[Union[str, list[str]]], default_recipients: list[str]
) -> Optional[list[str]]:
    """Normalize target parameter to a list of recipients.

    Args:
        target: Single target or list of targets
        default_recipients: Default recipients to use if target is None

    Returns:
        List of target recipients, or None if validation fails
    """
    if not target:
        if not default_recipients:
            _LOGGER.error(
                "Target (phone number or group ID) is required "
                "and no default recipients configured"
            )
            return None
        return default_recipients

    # Ensure target is a list
    if isinstance(target, str):
        return [target]
    return target


def prepare_message(message: str, title: Optional[str]) -> str:
    """Prepare the full message with optional title.

    Args:
        message: The message content
        title: Optional title to prepend

    Returns:
        Full message with title prepended if provided
    """
    if title:
        return f"{title}\n\n{message}"
    return message
