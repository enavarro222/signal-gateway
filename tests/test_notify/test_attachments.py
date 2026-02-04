"""Tests for notify service attachment processing."""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# Test encode_attachments_from_paths
def test_encode_attachments_success(attachment_processor):
    """Test encoding attachments from paths."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"test content")
        tmp.flush()
        tmp_path = tmp.name

    try:
        result = attachment_processor.encode_attachments_from_paths([tmp_path])
        assert len(result) == 1
        # Verify it's base64 encoded
        import base64

        decoded = base64.b64decode(result[0])
        assert decoded == b"test content"
    finally:
        os.unlink(tmp_path)


def test_encode_attachments_file_not_found(attachment_processor):
    """Test encoding non-existent file."""
    with pytest.raises(ValueError, match="not found"):
        attachment_processor.encode_attachments_from_paths(["/nonexistent.txt"])


def test_encode_attachments_too_large(attachment_processor):
    """Test encoding file exceeding size limit."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        # Write 51 MB
        tmp.write(b"x" * (51 * 1024 * 1024))
        tmp.flush()
        tmp_path = tmp.name

    try:
        with pytest.raises(ValueError, match="exceeds maximum"):
            attachment_processor.encode_attachments_from_paths([tmp_path])
    finally:
        os.unlink(tmp_path)


def test_encode_attachments_multiple_files(attachment_processor):
    """Test encoding multiple attachments."""
    files = []
    try:
        for i in range(2):
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            tmp.write(f"content{i}".encode())
            tmp.flush()
            files.append(tmp.name)
            tmp.close()

        result = attachment_processor.encode_attachments_from_paths(files)
        assert len(result) == 2
    finally:
        for f in files:
            os.unlink(f)


# Test _validate_content_length
def test_validate_content_length_ok(attachment_processor):
    """Test content length validation with acceptable size."""
    # Should not raise
    attachment_processor._validate_content_length("1000", 2000)


def test_validate_content_length_too_large(attachment_processor):
    """Test content length validation with size exceeding limit."""
    # Should raise when Content-Length exceeds max_size
    with pytest.raises(ValueError):
        attachment_processor._validate_content_length("2000", 1000)


def test_validate_content_length_none(attachment_processor):
    """Test content length validation with no header."""
    # Should not raise
    attachment_processor._validate_content_length(None, 1000)


# Test _download_in_chunks
@pytest.mark.asyncio
async def test_download_in_chunks_success(attachment_processor):
    """Test successful chunk download."""
    mock_response = MagicMock()

    chunks_data = [b"chunk1", b"chunk2"]

    async def mock_iter_chunked(size):
        for chunk in chunks_data:
            yield chunk

    mock_response.content.iter_chunked = mock_iter_chunked

    result = await attachment_processor._download_in_chunks(mock_response, 10000)
    assert result == b"chunk1chunk2"


@pytest.mark.asyncio
async def test_download_in_chunks_exceeds_limit(attachment_processor):
    """Test download exceeding size limit."""
    mock_response = MagicMock()

    async def mock_iter_chunked(size):
        # Yield chunks that exceed the limit
        for _ in range(10):
            yield b"x" * 1000

    mock_response.content.iter_chunked = mock_iter_chunked

    with pytest.raises(ValueError):
        await attachment_processor._download_in_chunks(mock_response, 100)


# Test _download_and_encode_url
@pytest.mark.asyncio
async def test_download_and_encode_url_success(attachment_processor):
    """Test successful download and encoding from URL."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": "1000"}  # Use dict instead of mock

    async def mock_iter_chunked(size):
        yield b"test content from url"

    mock_response.content.iter_chunked = mock_iter_chunked
    mock_response.raise_for_status = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    result = await attachment_processor._download_and_encode_url(
        mock_session, "https://example.com/file.jpg", 10000
    )

    assert result is not None
    # Verify it's base64 encoded
    import base64

    decoded = base64.b64decode(result)
    assert decoded == b"test content from url"
    mock_response.raise_for_status.assert_called_once()


@pytest.mark.asyncio
async def test_download_and_encode_url_exceeds_size(attachment_processor):
    """Test download failing when content exceeds size limit."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.headers = {"Content-Length": "100000"}  # Large Content-Length
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(ValueError, match="too large"):
        await attachment_processor._download_and_encode_url(
            mock_session, "https://example.com/large.jpg", 1000
        )


@pytest.mark.asyncio
async def test_download_and_encode_url_http_error(attachment_processor):
    """Test download failing with HTTP error."""
    from aiohttp import ClientResponseError, RequestInfo
    from yarl import URL

    mock_session = MagicMock()
    mock_response = MagicMock()

    # Create proper RequestInfo for the exception
    request_info = RequestInfo(
        url=URL("https://example.com/notfound.jpg"),
        method="GET",
        headers={},
        real_url=URL("https://example.com/notfound.jpg"),
    )

    mock_response.raise_for_status.side_effect = ClientResponseError(
        request_info=request_info, history=(), status=404, message="Not Found"
    )
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with pytest.raises(ClientResponseError):
        await attachment_processor._download_and_encode_url(
            mock_session, "https://example.com/notfound.jpg", 10000
        )


# Test process_attachments
@pytest.mark.asyncio
async def test_process_attachments_both_local_and_urls(attachment_processor):
    """Test processing both local files and URLs."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"local")
        tmp.flush()
        tmp_path = tmp.name

    try:
        # Mock URL download
        with patch.object(
            attachment_processor,
            "download_attachments_from_urls",
            return_value=["url_base64"],
        ):
            result = await attachment_processor.process_attachments(
                attachments=[tmp_path],
                urls=["https://example.com/file.jpg"],
                verify_ssl=True,
            )

            assert result is not None
            assert len(result) == 2  # 1 local + 1 url
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_process_attachments_exception_propagates(attachment_processor):
    """Test that exceptions in attachment processing propagate to the caller."""
    with pytest.raises(ValueError, match="Attachment file not found"):
        await attachment_processor.process_attachments(
            attachments=["/nonexistent.txt"], urls=None, verify_ssl=True
        )
