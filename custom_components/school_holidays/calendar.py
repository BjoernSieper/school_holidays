"""Calendar: school holidays, public holidays and user-defined free days.

School and public holidays come from openholidaysapi.org and are read-only. Events
created in the calendar (UI or ``calendar.create_event``) are stored as free days;
only those can be edited or deleted.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityFeature,
    CalendarEvent,
)
from homeassistant.components.calendar.const import (
    EVENT_DESCRIPTION,
    EVENT_END,
    EVENT_RRULE,
    EVENT_START,
    EVENT_SUMMARY,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import logic
from .const import DOMAIN
from .coordinator import SchoolHolidaysConfigEntry, SchoolHolidaysCoordinator
from .entity import SchoolHolidaysEntity

# Prefix for the read-only events, so they stand out from the user's free days.
_PREFIX = {logic.KIND_SCHOOL: "🎒 ", logic.KIND_PUBLIC: "🎉 "}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolHolidaysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the calendar."""
    async_add_entities([SchoolHolidaysCalendar(entry.runtime_data)])


def _to_event(p: logic.Period) -> CalendarEvent:
    """All-day event; Home Assistant expects an exclusive end date."""
    return CalendarEvent(
        start=p.start,
        end=p.end + timedelta(days=1),
        summary=f"{_PREFIX.get(p.kind, '')}{p.name}".strip() or p.kind,
        description=p.description,
        uid=p.uid,  # None for read-only events -> no edit/delete in the UI
    )


def _local_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return dt_util.as_local(value).date()
    return value


def _inclusive_range(dtstart: date | datetime, dtend: date | datetime | None) -> tuple[date, date]:
    """Turn a calendar start/end (end exclusive) into the inclusive days it covers."""
    start = _local_date(dtstart)
    if dtend is None:
        return start, start
    if isinstance(dtend, datetime):
        local_end = dt_util.as_local(dtend)
        # An event ending exactly at midnight does not cover that day.
        end = local_end.date()
        if local_end.time() == datetime.min.time():
            end -= timedelta(days=1)
    else:
        end = dtend - timedelta(days=1)
    return start, max(start, end)


def _fields(event: dict[str, Any]) -> tuple[date, date, str, str | None]:
    if event.get(EVENT_RRULE):
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="recurring_not_supported"
        )
    start, end = _inclusive_range(event[EVENT_START], event.get(EVENT_END))
    summary = (event.get(EVENT_SUMMARY) or "").strip()
    return start, end, summary, event.get(EVENT_DESCRIPTION) or None


class SchoolHolidaysCalendar(SchoolHolidaysEntity, CalendarEntity):
    """All holidays of the region in one calendar; free days can be added there."""

    _attr_translation_key = "calendar"
    _attr_supported_features = (
        CalendarEntityFeature.CREATE_EVENT
        | CalendarEntityFeature.DELETE_EVENT
        | CalendarEntityFeature.UPDATE_EVENT
    )

    def __init__(self, coordinator: SchoolHolidaysCoordinator) -> None:
        super().__init__(coordinator, "calendar")

    @property
    def event(self) -> CalendarEvent | None:
        """The event running today, else the next one."""
        nxt = logic.current_or_next(dt_util.now().date(), self.coordinator.all_periods)
        return _to_event(nxt) if nxt else None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Events overlapping the requested window."""
        first, last = _inclusive_range(start_date, end_date)
        return [
            _to_event(p) for p in self.coordinator.all_periods if p.start <= last and p.end >= first
        ]

    async def async_create_event(self, **kwargs: Any) -> None:
        """Add a free day (or a range of free days)."""
        start, end, summary, description = _fields(kwargs)
        await self.coordinator.async_add_free_day(start, end, summary, description)

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Change a free day; holidays from the API cannot be changed."""
        self._check_editable(uid)
        start, end, summary, description = _fields(event)
        await self.coordinator.async_update_free_day(uid, start, end, summary, description)

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Delete a free day; holidays from the API cannot be deleted."""
        self._check_editable(uid)
        await self.coordinator.async_delete_free_day(uid)

    def _check_editable(self, uid: str) -> None:
        if uid not in self.coordinator.free_days:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="free_day_not_found"
            )
