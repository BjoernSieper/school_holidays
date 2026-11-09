"""Calendar, user-defined free days and the combined day-off sensors."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
import pytest

from custom_components.school_holidays import api
from custom_components.school_holidays.const import DOMAIN

API = "custom_components.school_holidays.api.async_get_school_holidays"

# Wednesday 2026-10-14; Thursday is the 15th.
TODAY = date(2026, 10, 14)
TOMORROW = TODAY + timedelta(days=1)


def _raw(start: date, end: date, name: str) -> dict:
    return {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "name": [{"language": "EN", "text": name}],
    }


@pytest.fixture(autouse=True)
def noon(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(
        dt_util.as_utc(datetime(2026, 10, 14, 12, 0, tzinfo=dt_util.get_default_time_zone()))
    )


async def _setup(hass: HomeAssistant, entry, school=None) -> None:
    entry.add_to_hass(hass)
    with patch(API, return_value=school or []):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _eid(hass: HomeAssistant, entry, platform: str, key: str) -> str:
    eid = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert eid, f"entity {platform}/{key} not registered"
    return eid


async def _events(hass: HomeAssistant, entity_id: str, start: date, end: date) -> list[dict]:
    resp = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": f"{start.isoformat()} 00:00:00",
            "end_date_time": f"{end.isoformat()} 00:00:00",
        },
        blocking=True,
        return_response=True,
    )
    return resp[entity_id]["events"]


async def _create(hass: HomeAssistant, entity_id: str, start: date, end: date, summary: str):
    """calendar.create_event with an exclusive end date, as Home Assistant expects."""
    await hass.services.async_call(
        "calendar",
        "create_event",
        {
            "entity_id": entity_id,
            "summary": summary,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        blocking=True,
    )
    await hass.async_block_till_done()


async def test_entity_ids(hass: HomeAssistant, config_entry) -> None:
    """New entities get stable, readable entity IDs."""
    await _setup(hass, config_entry)
    assert _eid(hass, config_entry, "calendar", "calendar") == (
        "calendar.hesse_school_holidays_and_days_off"
    )
    assert _eid(hass, config_entry, "binary_sensor", "free_day_today") == (
        "binary_sensor.hesse_free_day_today"
    )
    assert _eid(hass, config_entry, "binary_sensor", "day_off_tomorrow") == (
        "binary_sensor.hesse_day_off_tomorrow"
    )


async def test_calendar_shows_school_and_public_holidays(
    hass: HomeAssistant, config_entry, public_holidays_api
) -> None:
    """Both API sources appear as read-only all-day events (exclusive end)."""
    public_holidays_api.return_value = [_raw(date(2026, 10, 3), date(2026, 10, 3), "Unity Day")]
    await _setup(hass, config_entry, [_raw(date(2026, 10, 5), date(2026, 10, 17), "Autumn")])
    cal = _eid(hass, config_entry, "calendar", "calendar")

    events = await _events(hass, cal, date(2026, 10, 1), date(2026, 11, 1))
    assert [(e["summary"], e["start"], e["end"]) for e in events] == [
        ("🎉 Unity Day", "2026-10-03", "2026-10-04"),
        ("🎒 Autumn", "2026-10-05", "2026-10-18"),
    ]
    # The running event is the calendar's state.
    state = hass.states.get(cal)
    assert state.state == "on"
    assert state.attributes["message"] == "🎒 Autumn"
    # Public holidays are fetched for the same window and region.
    args = public_holidays_api.call_args.args
    assert args[1:4] == ("DE", "DE-HE", "2026-04-17")


async def test_create_free_day_turns_on_sensors(hass: HomeAssistant, config_entry) -> None:
    """A free day created in the calendar drives the free-day and day-off sensors."""
    await _setup(hass, config_entry)
    cal = _eid(hass, config_entry, "calendar", "calendar")
    free_tomorrow = _eid(hass, config_entry, "binary_sensor", "free_day_tomorrow")
    off_tomorrow = _eid(hass, config_entry, "binary_sensor", "day_off_tomorrow")
    school_tomorrow = _eid(hass, config_entry, "binary_sensor", "tomorrow")
    assert hass.states.get(free_tomorrow).state == "off"
    assert hass.states.get(off_tomorrow).state == "off"

    await _create(hass, cal, TOMORROW, TOMORROW + timedelta(days=1), "Movable day")

    state = hass.states.get(free_tomorrow)
    assert state.state == "on"
    assert state.attributes["name"] == "Movable day"
    assert state.attributes["start_date"] == state.attributes["end_date"] == "2026-10-15"
    off = hass.states.get(off_tomorrow)
    assert off.state == "on"
    assert off.attributes == off.attributes | {
        "free_day": "Movable day",
        "school_holiday": None,
        "public_holiday": None,
    }
    # The school-holiday sensors stay school holidays only.
    assert hass.states.get(school_tomorrow).state == "off"
    assert hass.states.get(_eid(hass, config_entry, "binary_sensor", "free_day_today")).state == (
        "off"
    )

    events = await _events(hass, cal, TODAY, TODAY + timedelta(days=7))
    assert len(events) == 1
    assert (events[0]["summary"], events[0]["start"], events[0]["end"]) == (
        "Movable day",
        "2026-10-15",
        "2026-10-16",
    )


async def test_day_off_combines_sources(
    hass: HomeAssistant, config_entry, public_holidays_api
) -> None:
    """Day off is on for a public holiday alone and lists every source."""
    public_holidays_api.return_value = [_raw(TODAY, TODAY, "Holiday")]
    await _setup(hass, config_entry, [_raw(TODAY - timedelta(days=2), TODAY, "Autumn")])
    off_today = hass.states.get(_eid(hass, config_entry, "binary_sensor", "day_off_today"))
    off_tomorrow = hass.states.get(_eid(hass, config_entry, "binary_sensor", "day_off_tomorrow"))
    assert off_today.state == "on"
    assert off_today.attributes["school_holiday"] == "Autumn"
    assert off_today.attributes["public_holiday"] == "Holiday"
    assert off_today.attributes["free_day"] is None
    assert off_tomorrow.state == "off"


async def test_update_and_delete_free_day(
    hass: HomeAssistant, config_entry, hass_ws_client
) -> None:
    """Free days can be edited and deleted through the calendar UI (websocket API)."""
    await _setup(hass, config_entry)
    cal = _eid(hass, config_entry, "calendar", "calendar")
    free_today = _eid(hass, config_entry, "binary_sensor", "free_day_today")
    await _create(hass, cal, TOMORROW, TOMORROW + timedelta(days=1), "Bridge day")
    uid = config_entry.runtime_data.free_days.periods[0].uid
    client = await hass_ws_client(hass)

    await client.send_json_auto_id(
        {
            "type": "calendar/event/update",
            "entity_id": cal,
            "uid": uid,
            "event": {
                "summary": "Bridge days",
                "dtstart": TODAY.isoformat(),
                "dtend": (TOMORROW + timedelta(days=1)).isoformat(),
            },
        }
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    state = hass.states.get(free_today)
    assert state.state == "on"
    assert (state.attributes["name"], state.attributes["end_date"]) == ("Bridge days", "2026-10-15")

    await client.send_json_auto_id({"type": "calendar/event/delete", "entity_id": cal, "uid": uid})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert hass.states.get(free_today).state == "off"
    assert await _events(hass, cal, TODAY, TODAY + timedelta(days=7)) == []


async def test_api_events_are_read_only(hass: HomeAssistant, config_entry) -> None:
    """School holidays have no uid; unknown uids cannot be changed or deleted."""
    await _setup(hass, config_entry, [_raw(TOMORROW, TOMORROW, "Autumn")])
    cal = _eid(hass, config_entry, "calendar", "calendar")
    entity = hass.data["entity_components"]["calendar"].get_entity(cal)
    (event,) = await entity.async_get_events(
        hass, dt_util.start_of_local_day(TODAY), dt_util.start_of_local_day(TODAY + timedelta(7))
    )
    assert event.uid is None
    assert event.summary == "🎒 Autumn"

    entity = hass.data["entity_components"]["calendar"].get_entity(cal)
    with pytest.raises(HomeAssistantError) as err:
        await entity.async_delete_event("nope")
    assert err.value.translation_key == "free_day_not_found"
    with pytest.raises(HomeAssistantError):
        await entity.async_update_event(
            "nope", {"summary": "x", "dtstart": TODAY, "dtend": TOMORROW}
        )


async def test_recurring_events_rejected(hass: HomeAssistant, config_entry) -> None:
    """RRULEs are rejected with a translated error instead of being ignored."""
    await _setup(hass, config_entry)
    cal = _eid(hass, config_entry, "calendar", "calendar")
    entity = hass.data["entity_components"]["calendar"].get_entity(cal)
    with pytest.raises(HomeAssistantError) as err:
        await entity.async_create_event(
            summary="Weekly", dtstart=TODAY, dtend=TOMORROW, rrule="FREQ=WEEKLY"
        )
    assert err.value.translation_key == "recurring_not_supported"


async def test_timed_event_covers_its_days(hass: HomeAssistant, config_entry) -> None:
    """A timed event is stored as the local days it touches (midnight end excluded)."""
    await _setup(hass, config_entry)
    cal = _eid(hass, config_entry, "calendar", "calendar")
    entity = hass.data["entity_components"]["calendar"].get_entity(cal)
    tz = dt_util.get_default_time_zone()
    await entity.async_create_event(
        summary="Trip",
        dtstart=datetime(2026, 10, 15, 8, 0, tzinfo=tz),
        dtend=datetime(2026, 10, 17, 0, 0, tzinfo=tz),
    )
    await hass.async_block_till_done()
    (period,) = config_entry.runtime_data.free_days.periods
    assert (period.start, period.end) == (date(2026, 10, 15), date(2026, 10, 16))


async def test_free_days_persist_and_survive_api_errors(hass: HomeAssistant, config_entry) -> None:
    """Free days are stored, reloaded and independent of the holiday API."""
    await _setup(hass, config_entry)
    cal = _eid(hass, config_entry, "calendar", "calendar")
    await _create(hass, cal, TODAY, TOMORROW, "Teacher training")

    with patch(API, return_value=[]):
        assert await hass.config_entries.async_reload(config_entry.entry_id)
        await hass.async_block_till_done()
    free_today = _eid(hass, config_entry, "binary_sensor", "free_day_today")
    assert hass.states.get(free_today).state == "on"

    with patch(API, side_effect=api.OpenHolidaysError("down")):
        await config_entry.runtime_data.async_refresh()
    assert hass.states.get(free_today).state == "on"


async def test_public_holiday_error_keeps_school_data(
    hass: HomeAssistant, config_entry, public_holidays_api
) -> None:
    """A failing public-holiday request does not break setup or school holidays."""
    public_holidays_api.side_effect = api.OpenHolidaysError("down")
    await _setup(hass, config_entry, [_raw(TODAY, TOMORROW, "Autumn")])
    assert hass.states.get(_eid(hass, config_entry, "binary_sensor", "today")).state == "on"
    off = hass.states.get(_eid(hass, config_entry, "binary_sensor", "day_off_today"))
    assert (off.state, off.attributes["public_holiday"]) == ("on", None)


async def test_remove_entry_deletes_free_days(
    hass: HomeAssistant, config_entry, hass_storage
) -> None:
    """Deleting the integration entry also deletes its stored free days."""
    await _setup(hass, config_entry)
    cal = _eid(hass, config_entry, "calendar", "calendar")
    await _create(hass, cal, TODAY, TOMORROW, "Free")
    key = f"{DOMAIN}.{config_entry.entry_id}.free_days"
    assert hass_storage[key]["data"]["free_days"][0]["name"] == "Free"

    await hass.config_entries.async_remove(config_entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage
