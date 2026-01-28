"""Tests for parse_recipients function."""

from custom_components.signal_gateway import parse_recipients


def test_single_recipient():
    """Test parsing a single recipient."""
    result = parse_recipients("+1234567890")
    assert result == ["+1234567890"]


def test_comma_separated():
    """Test parsing comma-separated recipients."""
    result = parse_recipients("+1234567890, +9876543210")
    assert result == ["+1234567890", "+9876543210"]


def test_newline_separated():
    """Test parsing newline-separated recipients."""
    result = parse_recipients("+1234567890\n+9876543210")
    assert result == ["+1234567890", "+9876543210"]


def test_mixed_separators():
    """Test parsing with both commas and newlines."""
    result = parse_recipients("+1234567890, +9876543210\n+5551234567")
    assert result == ["+1234567890", "+9876543210", "+5551234567"]


def test_whitespace_handling():
    """Test that whitespace is properly stripped."""
    result = parse_recipients("  +1234567890  ,  +9876543210  ")
    assert result == ["+1234567890", "+9876543210"]


def test_empty_string():
    """Test parsing an empty string."""
    result = parse_recipients("")
    assert result == []


def test_whitespace_only():
    """Test parsing a string with only whitespace."""
    result = parse_recipients("  \n  \n  ")
    assert result == []


def test_trailing_comma():
    """Test parsing with trailing comma."""
    result = parse_recipients("+1234567890,")
    assert result == ["+1234567890"]


def test_multiple_commas():
    """Test parsing with multiple consecutive commas."""
    result = parse_recipients("+1234567890,,+9876543210")
    assert result == ["+1234567890", "+9876543210"]


def test_empty_lines():
    """Test parsing with empty lines."""
    result = parse_recipients("+1234567890\n\n+9876543210")
    assert result == ["+1234567890", "+9876543210"]


def test_complex_mixed_format():
    """Test parsing a complex mixed format."""
    result = parse_recipients(
        "+1234567890, +9876543210\n"
        "+5551234567\n"
        "\n"
        "+4445556666, +7778889999, +1112223333\n"
        "+4567891230"
    )
    assert result == [
        "+1234567890",
        "+9876543210",
        "+5551234567",
        "+4445556666",
        "+7778889999",
        "+1112223333",
        "+4567891230",
    ]


def test_group_ids():
    """Test parsing group IDs (not just phone numbers)."""
    result = parse_recipients("group.abc123\ngroup.xyz789")
    assert result == ["group.abc123", "group.xyz789"]
