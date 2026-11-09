"""Tests for the thin openholidaysapi.org client."""

from __future__ import annotations

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import pytest

from custom_components.school_holidays import api

URL = f"{api.BASE}/SchoolHolidays"


async def test_school_holidays_ok(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(URL, json=[{"startDate": "2026-10-05", "endDate": "2026-10-17"}])
    data = await api.async_get_school_holidays(
        async_get_clientsession(hass), "DE", "DE-HE", "2026-10-01", "2026-12-31"
    )
    assert data == [{"startDate": "2026-10-05", "endDate": "2026-10-17"}]
    assert aioclient_mock.mock_calls[0][1].query["subdivisionCode"] == "DE-HE"


async def test_http_error_raises(hass: HomeAssistant, aioclient_mock) -> None:
    aioclient_mock.get(URL, status=503)
    with pytest.raises(api.OpenHolidaysError):
        await api.async_get_school_holidays(
            async_get_clientsession(hass), "DE", None, "2026-10-01", "2026-12-31"
        )


async def test_unexpected_payload_raises(hass: HomeAssistant, aioclient_mock) -> None:
    """A non-list JSON body (e.g. an error object) is treated as an API failure."""
    aioclient_mock.get(URL, json={"title": "Bad Request"})
    with pytest.raises(api.OpenHolidaysError):
        await api.async_get_school_holidays(
            async_get_clientsession(hass), "DE", None, "2026-10-01", "2026-12-31"
        )


@pytest.mark.parametrize("exc", [ClientError("boom"), TimeoutError()])
async def test_network_errors_raise(hass: HomeAssistant, aioclient_mock, exc) -> None:
    """Connection problems and timeouts are mapped to OpenHolidaysError."""
    aioclient_mock.get(URL, exc=exc)
    with pytest.raises(api.OpenHolidaysError):
        await api.async_get_school_holidays(
            async_get_clientsession(hass), "DE", None, "2026-10-01", "2026-12-31"
        )


async def test_invalid_json_raises(hass: HomeAssistant, aioclient_mock) -> None:
    """A body that is not JSON is mapped to OpenHolidaysError."""
    aioclient_mock.get(URL, text="<html>maintenance</html>")
    with pytest.raises(api.OpenHolidaysError):
        await api.async_get_school_holidays(
            async_get_clientsession(hass), "DE", None, "2026-10-01", "2026-12-31"
        )


async def test_countries_localized_and_sorted(hass: HomeAssistant, aioclient_mock) -> None:
    """Country names use the requested language and are sorted by name."""
    aioclient_mock.get(
        f"{api.BASE}/Countries",
        json=[
            {"isoCode": "FR", "name": [{"language": "DE", "text": "Frankreich"}]},
            {
                "isoCode": "AT",
                "name": [
                    {"language": "EN", "text": "Austria"},
                    {"language": "DE", "text": "Österreich"},
                ],
            },
            {"isoCode": "DE", "name": [{"language": "DE", "text": "Deutschland"}]},
            {"name": []},
        ],
    )
    out = await api.async_get_countries(async_get_clientsession(hass), "de")
    assert out == [
        {"code": "DE", "name": "Deutschland"},
        {"code": "FR", "name": "Frankreich"},
        {"code": "AT", "name": "Österreich"},
    ]


async def test_public_holidays_ok(hass: HomeAssistant, aioclient_mock) -> None:
    """Public holidays use the same window/region parameters as school holidays."""
    payload = [{"startDate": "2026-10-03", "endDate": "2026-10-03", "nationwide": True}]
    aioclient_mock.get(f"{api.BASE}/PublicHolidays", json=payload)
    data = await api.async_get_public_holidays(
        async_get_clientsession(hass), "de", "DE-HE", "2026-10-01", "2026-12-31", "de"
    )
    assert data == payload
    query = aioclient_mock.mock_calls[0][1].query
    assert query["countryIsoCode"] == "DE"
    assert query["subdivisionCode"] == "DE-HE"
    assert query["languageIsoCode"] == "DE"
