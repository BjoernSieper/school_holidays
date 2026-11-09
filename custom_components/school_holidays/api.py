"""Thin async client for the free openholidaysapi.org (no API key)."""

from __future__ import annotations

import asyncio

from aiohttp import ClientError, ClientSession

from .logic import pick_name

BASE = "https://openholidaysapi.org"
TIMEOUT = 20


class OpenHolidaysError(Exception):
    """Raised when the API cannot be reached or returns an error."""


async def _get(session: ClientSession, path: str, params: dict) -> list[dict]:
    url = f"{BASE}/{path}"
    try:
        async with (
            asyncio.timeout(TIMEOUT),
            session.get(url, params=params, headers={"Accept": "application/json"}) as resp,
        ):
            # The context manager releases the connection back to HA's shared
            # session pool on every path (including non-200 responses).
            if resp.status != 200:
                raise OpenHolidaysError(f"{path} -> HTTP {resp.status}")
            data = await resp.json()
    except (ClientError, TimeoutError, ValueError) as err:
        # ValueError covers JSON decode errors (json.JSONDecodeError).
        raise OpenHolidaysError(f"{path} request failed: {err}") from err
    if not isinstance(data, list):
        raise OpenHolidaysError(f"{path} returned an unexpected payload")
    return data


async def async_get_countries(session: ClientSession, language: str = "EN") -> list[dict]:
    """Return [{'code': ISO, 'name': localized}] for the country picker."""
    data = await _get(session, "Countries", {"languageIsoCode": language.upper()})
    out = [
        {"code": c.get("isoCode"), "name": pick_name(c.get("name"), language)}
        for c in data
        if c.get("isoCode")
    ]
    out.sort(key=lambda c: c["name"])
    return out


async def async_get_subdivisions(
    session: ClientSession, country: str, language: str = "EN"
) -> list[dict]:
    """Return [{'code': e.g. DE-HE, 'name': localized}] for a country."""
    data = await _get(
        session,
        "Subdivisions",
        {"countryIsoCode": country.upper(), "languageIsoCode": language.upper()},
    )
    out = [
        {"code": s.get("code"), "name": pick_name(s.get("name"), language)}
        for s in data
        if s.get("code")
    ]
    out.sort(key=lambda s: s["name"])
    return out


async def async_get_school_holidays(
    session: ClientSession,
    country: str,
    subdivision: str | None,
    valid_from: str,
    valid_to: str,
    language: str = "EN",
) -> list[dict]:
    """Return the raw SchoolHolidays list for the given window."""
    params = {
        "countryIsoCode": country.upper(),
        "languageIsoCode": language.upper(),
        "validFrom": valid_from,
        "validTo": valid_to,
    }
    if subdivision:
        params["subdivisionCode"] = subdivision
    return await _get(session, "SchoolHolidays", params)


async def async_get_public_holidays(
    session: ClientSession,
    country: str,
    subdivision: str | None,
    valid_from: str,
    valid_to: str,
    language: str = "EN",
) -> list[dict]:
    """Return the raw PublicHolidays list (nationwide + the region's own) for the window."""
    params = {
        "countryIsoCode": country.upper(),
        "languageIsoCode": language.upper(),
        "validFrom": valid_from,
        "validTo": valid_to,
    }
    if subdivision:
        params["subdivisionCode"] = subdivision
    return await _get(session, "PublicHolidays", params)
