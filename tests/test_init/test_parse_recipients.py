"""Tests for parse_recipients function."""

from custom_components.signal_gateway import parse_recipients


def test_parse_recipients_empty_string():
    """Test parsing empty string."""
    assert parse_recipients("") == []


def test_parse_recipients_whitespace_only():
    """Test parsing whitespace only."""
    assert parse_recipients("  \n  \n  ") == []


def test_parse_recipients_single_recipient():
    """Test parsing single recipient."""
    assert parse_recipients("+1234567890") == ["+1234567890"]


def test_parse_recipients_comma_separated():
    """Test parsing comma-separated recipients."""
    result = parse_recipients("+1234567890, +9876543210")
    assert result == ["+1234567890", "+9876543210"]


def test_parse_recipients_newline_separated():
    """Test parsing newline-separated recipients."""
    result = parse_recipients("+1234567890\n+9876543210")
    assert result == ["+1234567890", "+9876543210"]


def test_parse_recipients_mixed_separators():
    """Test parsing mixed newlines and commas."""
    result = parse_recipients("+1234567890, +9876543210\n+5551234567")
    assert result == ["+1234567890", "+9876543210", "+5551234567"]


def test_parse_recipients_whitespace_handling():
    """Test that whitespace is properly stripped."""
    result = parse_recipients("  +1234567890  ,  +9876543210  ")
    assert result == ["+1234567890", "+9876543210"]


def test_parse_recipients_trailing_comma():
    """Test handling trailing comma."""
    result = parse_recipients("+1234567890,")
    assert result == ["+1234567890"]


def test_parse_recipients_multiple_commas():
    """Test handling multiple consecutive commas."""
    result = parse_recipients("+1234567890,,+9876543210")
    assert result == ["+1234567890", "+9876543210"]


def test_parse_recipients_empty_lines():
    """Test handling empty lines."""
    result = parse_recipients("+1234567890\n\n+9876543210")
    assert result == ["+1234567890", "+9876543210"]
