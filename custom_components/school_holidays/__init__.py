"""The School Holidays integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import (
    SchoolHolidaysConfigEntry,
    SchoolHolidaysCoordinator,
    stale_issue_id,
)
from .free_days import async_remove_store

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SchoolHolidaysConfigEntry) -> bool:
    """Set up School Holidays from a config entry."""
    coordinator = SchoolHolidaysCoordinator(hass, entry)
    await coordinator.async_setup()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SchoolHolidaysConfigEntry) -> bool:
    """Unload a config entry (the coordinator and midnight timer stop via async_on_unload)."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: SchoolHolidaysConfigEntry) -> None:
    """Drop a pending repair issue and the stored free days when the entry is deleted."""
    ir.async_delete_issue(hass, DOMAIN, stale_issue_id(entry.entry_id))
    await async_remove_store(hass, entry.entry_id)


async def _async_update_listener(hass: HomeAssistant, entry: SchoolHolidaysConfigEntry) -> None:
    """Reload the entry when its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
