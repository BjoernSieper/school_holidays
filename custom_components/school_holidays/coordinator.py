"""DataUpdateCoordinator for School Holidays."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import api, logic
from .const import (
    CONF_COUNTRY,
    CONF_COUNTRY_NAME,
    CONF_LANGUAGE,
    CONF_SUBDIVISION,
    CONF_SUBDIVISION_NAME,
    CONF_UPDATE_HOURS,
    DATA_CURRENT,
    DATA_DAY_OFF_TODAY,
    DATA_DAY_OFF_TOMORROW,
    DATA_FREE_DAYS,
    DATA_FREE_TODAY,
    DATA_FREE_TOMORROW,
    DATA_LAST_SUCCESS,
    DATA_NEXT,
    DATA_PERIODS,
    DATA_PUBLIC_HOLIDAYS,
    DATA_TODAY,
    DATA_TOMORROW,
    DATA_TOMORROW_PERIOD,
    DEFAULT_LANGUAGE,
    DEFAULT_UPDATE_HOURS,
    DOMAIN,
    ISSUE_STALE_DATA,
    LANGUAGE_AUTO,
    LOOKAHEAD_DAYS,
    LOOKBACK_DAYS,
    MAX_UPDATE_HOURS,
    MIN_UPDATE_HOURS,
    STALE_AFTER,
)
from .free_days import FreeDayStore

_LOGGER = logging.getLogger(__name__)

type SchoolHolidaysConfigEntry = ConfigEntry[SchoolHolidaysCoordinator]


def _period_dict(p: logic.Period | None) -> dict | None:
    if p is None:
        return None
    out = {"name": p.name, "start": p.start.isoformat(), "end": p.end.isoformat()}
    if p.kind == logic.KIND_CUSTOM:
        out["description"] = p.description
    return out


def _day_off(
    day,
    school: list[logic.Period],
    public: list[logic.Period],
    custom: list[logic.Period],
) -> dict[str, Any]:
    """Which sources make ``day`` a day off (name of each, or None)."""
    found = {
        "school_holiday": logic.period_on(day, school),
        "public_holiday": logic.period_on(day, public),
        "free_day": logic.period_on(day, custom),
    }
    return {
        "on": any(p is not None for p in found.values()),
        **{key: (p.name if p is not None else None) for key, p in found.items()},
    }


def stale_issue_id(entry_id: str) -> str:
    """Repair-issue id for an entry whose data has not been refreshed for too long."""
    return f"{ISSUE_STALE_DATA}_{entry_id}"


class SchoolHolidaysCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches holiday periods and derives today/tomorrow/next, robustly."""

    config_entry: SchoolHolidaysConfigEntry

    def __init__(self, hass: HomeAssistant, entry: SchoolHolidaysConfigEntry) -> None:
        opts = {**entry.data, **entry.options}
        self.country: str = opts[CONF_COUNTRY]
        self.subdivision: str | None = opts.get(CONF_SUBDIVISION) or None
        self.language_setting: str = opts.get(CONF_LANGUAGE) or LANGUAGE_AUTO
        hours = int(opts.get(CONF_UPDATE_HOURS, DEFAULT_UPDATE_HOURS))
        hours = min(MAX_UPDATE_HOURS, max(MIN_UPDATE_HOURS, hours))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title} ({entry.entry_id})",
            update_interval=timedelta(hours=hours),
        )
        self._periods: list[logic.Period] = []
        self._public: list[logic.Period] = []
        self.free_days = FreeDayStore(hass, entry.entry_id)
        self.last_successful_update: datetime | None = None

    @property
    def entry(self) -> SchoolHolidaysConfigEntry:
        """The config entry this coordinator belongs to."""
        return self.config_entry

    @property
    def region_name(self) -> str:
        """Human-readable region (subdivision, else country) for messages."""
        opts = {**self.config_entry.data, **self.config_entry.options}
        return (
            opts.get(CONF_SUBDIVISION_NAME)
            or opts.get(CONF_COUNTRY_NAME)
            or self.config_entry.title
            or self.country
        )

    @property
    def language(self) -> str:
        """ISO 639-1 code used for holiday names (resolved from HA if set to auto)."""
        if self.language_setting.lower() == LANGUAGE_AUTO:
            return logic.iso_language(self.hass.config.language, DEFAULT_LANGUAGE)
        return logic.iso_language(self.language_setting, DEFAULT_LANGUAGE)

    async def async_setup(self) -> None:
        """Load free days, first refresh, midnight rollover and language listener."""
        await self.free_days.async_load()
        await self.async_config_entry_first_refresh()
        # Recompute today/tomorrow at local midnight WITHOUT a network call, so
        # the sensors flip exactly at the day boundary even if the API is down.
        self.config_entry.async_on_unload(
            async_track_time_change(self.hass, self._handle_midnight, hour=0, minute=0, second=5)
        )
        if self.language_setting.lower() == LANGUAGE_AUTO:
            self.config_entry.async_on_unload(
                self.hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, self._handle_core_config)
            )

    @callback
    def _handle_midnight(self, _now: datetime) -> None:
        self.async_set_updated_data(self._derive())

    @callback
    def _handle_core_config(self, event: Event) -> None:
        """Re-fetch holiday names when the Home Assistant language changes."""
        if "language" in (event.data or {}):
            self.config_entry.async_create_background_task(
                self.hass, self.async_request_refresh(), f"{DOMAIN}_language_refresh"
            )

    @property
    def school_periods(self) -> list[logic.Period]:
        """School holidays from the API, sorted (for the school-holidays calendar)."""
        return self._periods

    @property
    def public_periods(self) -> list[logic.Period]:
        """Public holidays from the API, sorted (for the public-holidays calendar)."""
        return self._public

    async def async_add_free_day(self, start, end, name: str, description: str | None) -> str:
        """Store a new free day and update all entities right away."""
        uid = await self.free_days.async_add(start, end, name, description)
        self.async_set_updated_data(self._derive())
        return uid

    async def async_update_free_day(
        self, uid: str, start, end, name: str, description: str | None
    ) -> None:
        """Change a free day and update all entities right away."""
        await self.free_days.async_update(uid, start, end, name, description)
        self.async_set_updated_data(self._derive())

    async def async_delete_free_day(self, uid: str) -> None:
        """Delete a free day and update all entities right away."""
        await self.free_days.async_delete(uid)
        self.async_set_updated_data(self._derive())

    def _derive(self) -> dict[str, Any]:
        today = dt_util.now().date()
        tomorrow = today + timedelta(days=1)
        custom = self.free_days.periods
        nxt = logic.current_or_next(today, self._periods)
        nxt_dict = _period_dict(nxt)
        if nxt_dict is not None:
            nxt_dict["days_until"] = logic.days_until(today, nxt)
        return {
            DATA_PERIODS: len(self._periods),
            DATA_TODAY: logic.is_holiday(today, self._periods),
            DATA_TOMORROW: logic.is_holiday(tomorrow, self._periods),
            DATA_CURRENT: _period_dict(logic.period_on(today, self._periods)),
            DATA_TOMORROW_PERIOD: _period_dict(logic.period_on(tomorrow, self._periods)),
            DATA_NEXT: nxt_dict,
            DATA_LAST_SUCCESS: self.last_successful_update,
            DATA_PUBLIC_HOLIDAYS: len(self._public),
            DATA_FREE_DAYS: len(custom),
            DATA_FREE_TODAY: _period_dict(logic.period_on(today, custom)),
            DATA_FREE_TOMORROW: _period_dict(logic.period_on(tomorrow, custom)),
            DATA_DAY_OFF_TODAY: _day_off(today, self._periods, self._public, custom),
            DATA_DAY_OFF_TOMORROW: _day_off(tomorrow, self._periods, self._public, custom),
        }

    @callback
    def _check_stale(self) -> None:
        """Raise a repair issue once the cached data is older than STALE_AFTER."""
        if self.last_successful_update is None:
            return
        age = dt_util.utcnow() - self.last_successful_update
        if age < STALE_AFTER:
            return
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            stale_issue_id(self.config_entry.entry_id),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_STALE_DATA,
            translation_placeholders={
                "region": self.region_name,
                "days": str(age.days),
                "last_update": dt_util.as_local(self.last_successful_update).strftime(
                    "%Y-%m-%d %H:%M"
                ),
            },
        )

    async def _async_update_data(self) -> dict[str, Any]:
        today = dt_util.now().date()
        valid_from = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
        valid_to = (today + timedelta(days=LOOKAHEAD_DAYS)).isoformat()
        session = async_get_clientsession(self.hass)
        language = self.language
        try:
            raw = await api.async_get_school_holidays(
                session, self.country, self.subdivision, valid_from, valid_to, language
            )
        except api.OpenHolidaysError as err:
            if self.last_successful_update is None:
                # No cached data yet (e.g. the very first refresh): surface the
                # failure so Home Assistant retries the setup instead of silently
                # creating empty sensors. On the first refresh this becomes
                # ConfigEntryNotReady automatically.
                raise UpdateFailed(f"School holidays API unavailable: {err}") from err
            # Robustness: once we have data, keep the last known periods instead of
            # going unavailable, so automations keep working through API hiccups.
            # The cached window reaches LOOKAHEAD_DAYS ahead, so it stays usable;
            # a repair issue tells the user once it is getting old.
            _LOGGER.warning(
                "School holidays API failed for %s (%s); keeping data from %s",
                self.region_name,
                err,
                self.last_successful_update,
            )
            self._check_stale()
        else:
            self._periods = logic.parse_periods(raw, language)
            self.last_successful_update = dt_util.utcnow()
            ir.async_delete_issue(self.hass, DOMAIN, stale_issue_id(self.config_entry.entry_id))
        await self._async_update_public(session, valid_from, valid_to, language)
        return self._derive()

    async def _async_update_public(
        self, session, valid_from: str, valid_to: str, language: str
    ) -> None:
        """Fetch public holidays; a failure only keeps the previous ones (best effort)."""
        try:
            raw = await api.async_get_public_holidays(
                session, self.country, self.subdivision, valid_from, valid_to, language
            )
        except api.OpenHolidaysError as err:
            _LOGGER.warning(
                "Public holidays could not be fetched for %s (%s); keeping %d cached",
                self.region_name,
                err,
                len(self._public),
            )
            return
        self._public = logic.parse_periods(raw, language, logic.KIND_PUBLIC)
