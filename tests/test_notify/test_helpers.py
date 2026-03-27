"""Tests for notify service helper/transformation methods."""

import os
import tempfile
from pathlib import Path
import pytest

from custom_components.signal_gateway.notify.helpers import (
    fix_phone_number,
    normalize_targets,
    prepare_message,
)
from custom_components.signal_gateway.notify.service import (
    SignalGatewayNotificationService,
)


# Test fix_phone_number
def test_fix_phone_number_with_plus():
    """Test phone number that already has +."""
    result = fix_phone_number("+1234567890")
    assert result == "+1234567890"


def test_fix_phone_number_without_plus():
    """Test phone number missing +."""
    result = fix_phone_number("1234567890")
    assert result == "+1234567890"


def test_fix_phone_number_group_id():
    """Test that group IDs are not modified."""
    result = fix_phone_number("group.abc123")
    assert result == "group.abc123"


def test_fix_phone_number_non_numeric():
    """Test that non-numeric strings are not modified."""
    result = fix_phone_number("notanumber")
    assert result == "notanumber"


# Test _normalize_file_path (this is in AttachmentProcessor)
def test_normalize_file_path_success(attachment_processor):
    """Test normalizing valid file path."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test")
        tmp.flush()
        tmp_path = tmp.name

    try:
        result = attachment_processor._normalize_file_path(tmp_path)
        assert result == Path(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_normalize_file_path_with_file_scheme(attachment_processor):
    """Test normalizing file:// URL."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"test")
        tmp.flush()
        tmp_path = tmp.name

    try:
        result = attachment_processor._normalize_file_path(f"file://{tmp_path}")
        assert result == Path(tmp_path)
    finally:
        os.unlink(tmp_path)


def test_normalize_file_path_not_exists(attachment_processor):
    """Test normalizing non-existent file."""
    with pytest.raises(ValueError, match="not found"):
        attachment_processor._normalize_file_path("/nonexistent/file.txt")


def test_normalize_file_path_is_directory(attachment_processor):
    """Test normalizing directory path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="not a file"):
            attachment_processor._normalize_file_path(tmpdir)


# Test normalize_targets
def test_normalize_targets_string():
    """Test normalizing single string target."""
    result = normalize_targets("+9876543210", [])
    assert result == ["+9876543210"]


def test_normalize_targets_list():
    """Test normalizing list of targets."""
    result = normalize_targets(["+111", "+222"], [])
    assert result == ["+111", "+222"]


def test_normalize_targets_none_with_defaults():
    """Test normalizing None target with default recipients."""
    result = normalize_targets(None, ["+1234567890"])
    assert result == ["+1234567890"]


def test_normalize_targets_none_without_defaults():
    """Test normalizing None target without default recipients."""
    result = normalize_targets(None, [])
    assert result is None


# Test prepare_message
def test_prepare_message_without_title():
    """Test preparing message without title."""
    result = prepare_message("Hello", None)
    assert result == "Hello"


def test_prepare_message_with_title(notification_service):
    """Test preparing message with title."""


def test_prepare_message_with_title():
    """Test preparing message with title."""
    result = prepare_message("Body", "Title")
    assert result == "Title\n\nBody"
