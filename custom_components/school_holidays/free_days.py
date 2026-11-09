"""User-defined free days (e.g. movable school days off), stored per config entry."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from . import logic
from .const import DOMAIN, STORAGE_VERSION


def _storage_key(entry_id: str) -> str:
    return f"{DOMAIN}.{entry_id}.free_days"


class FreeDayStore:
    """Keeps the free days in ``.storage`` and hands them out as ``Period`` objects."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, _storage_key(entry_id))
        self._items: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        """Read the stored free days; broken items are skipped."""
        data = await self._store.async_load() or {}
        self._items = {}
        for item in data.get("free_days", []):
            uid = item.get("uid")
            if uid and logic.to_date(item.get("start")) and logic.to_date(item.get("end")):
                self._items[uid] = item

    @property
    def periods(self) -> list[logic.Period]:
        """All free days, sorted by start date."""
        out = [
            logic.Period(
                start=logic.to_date(item["start"]),
                end=logic.to_date(item["end"]),
                name=item.get("name") or "",
                kind=logic.KIND_CUSTOM,
                uid=uid,
                description=item.get("description") or None,
            )
            for uid, item in self._items.items()
        ]
        out.sort(key=lambda p: (p.start, p.end))
        return out

    def __contains__(self, uid: object) -> bool:
        return uid in self._items

    async def async_add(
        self, start: date, end: date, name: str, description: str | None = None
    ) -> str:
        """Add a free day (``end`` inclusive) and return its uid."""
        uid = uuid4().hex
        self._items[uid] = _item(uid, start, end, name, description)
        await self._async_save()
        return uid

    async def async_update(
        self, uid: str, start: date, end: date, name: str, description: str | None = None
    ) -> None:
        """Replace an existing free day."""
        if uid not in self._items:
            raise KeyError(uid)
        self._items[uid] = _item(uid, start, end, name, description)
        await self._async_save()

    async def async_delete(self, uid: str) -> None:
        """Delete a free day."""
        if uid not in self._items:
            raise KeyError(uid)
        del self._items[uid]
        await self._async_save()

    async def _async_save(self) -> None:
        await self._store.async_save({"free_days": list(self._items.values())})


async def async_remove_store(hass: HomeAssistant, entry_id: str) -> None:
    """Delete the storage file of a removed config entry."""
    await Store(hass, STORAGE_VERSION, _storage_key(entry_id)).async_remove()


def _item(uid: str, start: date, end: date, name: str, description: str | None) -> dict[str, Any]:
    if end < start:
        raise ValueError("end before start")
    return {
        "uid": uid,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "name": name,
        "description": description or "",
    }
