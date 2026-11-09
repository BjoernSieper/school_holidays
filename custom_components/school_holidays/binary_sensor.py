"""Binary sensors: school holidays today / tomorrow."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DATA_CURRENT,
    DATA_DAY_OFF_TODAY,
    DATA_DAY_OFF_TOMORROW,
    DATA_FREE_TODAY,
    DATA_FREE_TOMORROW,
    DATA_TODAY,
    DATA_TOMORROW,
    DATA_TOMORROW_PERIOD,
)
from .coordinator import SchoolHolidaysConfigEntry, SchoolHolidaysCoordinator
from .entity import SchoolHolidaysEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SchoolHolidaysConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the today / tomorrow binary sensors (school, free day, day off)."""
    coordinator = entry.runtime_data
    async_add_entities(
        [
            HolidayTodayBinarySensor(coordinator),
            HolidayTomorrowBinarySensor(coordinator),
            FreeDayBinarySensor(coordinator, "free_day_today", DATA_FREE_TODAY),
            FreeDayBinarySensor(coordinator, "free_day_tomorrow", DATA_FREE_TOMORROW),
            DayOffBinarySensor(coordinator, "day_off_today", DATA_DAY_OFF_TODAY),
            DayOffBinarySensor(coordinator, "day_off_tomorrow", DATA_DAY_OFF_TOMORROW),
        ]
    )


class _HolidayBinary(SchoolHolidaysEntity, BinarySensorEntity):
    """On while the given day is inside a holiday period.

    The attributes describe the period covering *that* day (today resp. tomorrow).
    """

    _data_key: str
    _period_key: str

    @property
    def is_on(self) -> bool | None:
        val = (self.coordinator.data or {}).get(self._data_key)
        return bool(val) if val is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        period = (self.coordinator.data or {}).get(self._period_key) or {}
        return {
            "holiday_name": period.get("name"),
            "start_date": period.get("start"),
            "end_date": period.get("end"),
        }


class HolidayTodayBinarySensor(_HolidayBinary):
    _attr_translation_key = "today"
    _data_key = DATA_TODAY
    _period_key = DATA_CURRENT

    def __init__(self, coordinator: SchoolHolidaysCoordinator) -> None:
        super().__init__(coordinator, "today")


class HolidayTomorrowBinarySensor(_HolidayBinary):
    _attr_translation_key = "tomorrow"
    _data_key = DATA_TOMORROW
    _period_key = DATA_TOMORROW_PERIOD

    def __init__(self, coordinator: SchoolHolidaysCoordinator) -> None:
        super().__init__(coordinator, "tomorrow")


class FreeDayBinarySensor(SchoolHolidaysEntity, BinarySensorEntity):
    """On while the day is one of the user-defined free days (from the calendar)."""

    def __init__(self, coordinator: SchoolHolidaysCoordinator, key: str, data_key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._data_key = data_key

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._data_key) is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        period = (self.coordinator.data or {}).get(self._data_key) or {}
        return {
            "name": period.get("name"),
            "description": period.get("description"),
            "start_date": period.get("start"),
            "end_date": period.get("end"),
        }


class DayOffBinarySensor(SchoolHolidaysEntity, BinarySensorEntity):
    """On if the day is a school holiday, a public holiday or a user-defined free day."""

    def __init__(self, coordinator: SchoolHolidaysCoordinator, key: str, data_key: str) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._data_key = data_key

    @property
    def is_on(self) -> bool | None:
        info = (self.coordinator.data or {}).get(self._data_key)
        return bool(info["on"]) if info else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        info = (self.coordinator.data or {}).get(self._data_key) or {}
        return {
            "school_holiday": info.get("school_holiday"),
            "public_holiday": info.get("public_holiday"),
            "free_day": info.get("free_day"),
        }
