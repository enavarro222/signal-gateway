"""Test configuration for Signal Gateway integration."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading of custom integrations in Home Assistant tests.

    This fixture is automatically applied to all tests (autouse=True) and enables
    Home Assistant to load custom components from custom_components/ directory.

    Required for:
    - End-to-end tests using the real 'hass' fixture
    - Tests that need to setup config entries
    - Any test that loads the signal_gateway integration

    Provided by pytest-homeassistant-custom-component package.
    """
    yield
