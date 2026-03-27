"""Shared fixtures for Signal API tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.signal_gateway.signal.http_client import SignalHTTPClient


@pytest.fixture
def http_client():
    """Create a SignalHTTPClient instance with mocked session."""
    session = MagicMock()
    return SignalHTTPClient(
        api_url="http://localhost:8080",
        phone_number="+33612345678",
        session=session,
    )


@pytest.fixture
def mock_response():
    """
    Create a mock aiohttp response factory.

    Returns a function that creates mock responses with custom data/errors.

    Usage:
        def test_something(mock_response):
            response = mock_response(json_data={"id": "123"})
            response_error = mock_response(side_effect=ClientError("error"))
    """

    def _create_mock_response(json_data=None, status=200, side_effect=None):
        """
        Create a mock aiohttp response that works with async context manager.

        Args:
            json_data: Data to return from response.json()
            status: HTTP status code
            side_effect: Exception to raise on __aenter__
        """
        response = AsyncMock()
        response.status = status
        response.raise_for_status = MagicMock()

        if json_data is not None:
            response.json = AsyncMock(return_value=json_data)

        # Make the mock work as async context manager
        if side_effect:
            response.__aenter__ = AsyncMock(side_effect=side_effect)
        else:
            response.__aenter__ = AsyncMock(return_value=response)
        response.__aexit__ = AsyncMock(return_value=False)

        return response

    return _create_mock_response
