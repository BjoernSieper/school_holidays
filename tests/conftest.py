"""Shared fixtures for the School Holidays tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.school_holidays.const import (
    CONF_COUNTRY,
    CONF_COUNTRY_NAME,
    CONF_LANGUAGE,
    CONF_SUBDIVISION,
    CONF_SUBDIVISION_NAME,
    DOMAIN,
)

COUNTRIES = [
    {"code": "DE", "name": "Germany"},
    {"code": "FR", "name": "France"},
]
SUBDIVISIONS = [
    {"code": "DE-HE", "name": "Hesse"},
    {"code": "DE-BY", "name": "Bavaria"},
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load the custom integration in every test."""
    yield


PUBLIC_API = "custom_components.school_holidays.api.async_get_public_holidays"


@pytest.fixture(autouse=True)
def public_holidays_api(request):
    """No public holidays unless a test sets ``return_value``/``side_effect``.

    The API client tests exercise the real function, so they are left alone.
    """
    if request.module.__name__.endswith("test_api"):
        yield None
        return
    with patch(PUBLIC_API, return_value=[]) as mock:
        yield mock


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured entry for Germany / Hesse."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Hesse",
        unique_id="DE:DE-HE",
        data={
            CONF_COUNTRY: "DE",
            CONF_COUNTRY_NAME: "Germany",
            CONF_SUBDIVISION: "DE-HE",
            CONF_SUBDIVISION_NAME: "Hesse",
            CONF_LANGUAGE: "EN",
        },
    )
