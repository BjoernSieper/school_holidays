"""Offline unit tests for the pure school-holiday logic (no HA needed)."""

from datetime import date
import importlib.util
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_LOGIC = _HERE.parent / "custom_components" / "school_holidays" / "logic.py"
_spec = importlib.util.spec_from_file_location("sh_logic", _LOGIC)
logic = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = logic  # dataclasses need the module registered
_spec.loader.exec_module(logic)


RAW = [
    {
        "startDate": "2026-06-29",
        "endDate": "2026-08-07",
        "name": [
            {"language": "DE", "text": "Sommerferien"},
            {"language": "EN", "text": "Summer break"},
        ],
    },
    {
        "startDate": "2026-10-05",
        "endDate": "2026-10-17",
        "name": [{"language": "DE", "text": "Herbstferien"}],
    },
]


def test_parse_periods_localized():
    ps = logic.parse_periods(RAW, "DE")
    assert len(ps) == 2
    assert ps[0].name == "Sommerferien"
    assert ps[0].start == date(2026, 6, 29) and ps[0].end == date(2026, 8, 7)
    # English pick
    assert logic.parse_periods(RAW, "EN")[0].name == "Summer break"


def test_parse_periods_sorted_and_robust():
    reversed_raw = [*reversed(RAW), {"startDate": "bad", "endDate": "x", "name": []}]
    ps = logic.parse_periods(reversed_raw, "DE")
    assert len(ps) == 2  # the invalid one is dropped
    assert ps[0].start < ps[1].start  # sorted ascending


def test_is_holiday_within_and_outside():
    ps = logic.parse_periods(RAW, "DE")
    assert logic.is_holiday(date(2026, 7, 29), ps) is True  # inside summer
    assert logic.is_holiday(date(2026, 6, 29), ps) is True  # boundary start
    assert logic.is_holiday(date(2026, 8, 7), ps) is True  # boundary end
    assert logic.is_holiday(date(2026, 8, 8), ps) is False  # day after
    assert logic.is_holiday(date(2026, 9, 1), ps) is False  # gap


def test_period_on():
    ps = logic.parse_periods(RAW, "DE")
    assert logic.period_on(date(2026, 7, 1), ps).name == "Sommerferien"
    assert logic.period_on(date(2026, 9, 1), ps) is None


def test_current_or_next():
    ps = logic.parse_periods(RAW, "DE")
    # during summer -> returns summer (current)
    assert logic.current_or_next(date(2026, 7, 1), ps).name == "Sommerferien"
    # in the gap -> next is autumn
    assert logic.current_or_next(date(2026, 9, 1), ps).name == "Herbstferien"
    # after everything -> None
    assert logic.current_or_next(date(2027, 1, 1), ps) is None


def test_days_until():
    ps = logic.parse_periods(RAW, "DE")
    autumn = ps[1]
    assert logic.days_until(date(2026, 9, 1), autumn) == 34  # until autumn start
    summer = ps[0]
    assert logic.days_until(date(2026, 7, 1), summer) == 0  # already running


def test_empty():
    assert logic.parse_periods([], "DE") == []
    assert logic.is_holiday(date(2026, 7, 29), []) is False
    assert logic.current_or_next(date(2026, 7, 29), []) is None
    assert logic.days_until(date(2026, 7, 29), None) is None


def test_iso_language():
    assert logic.iso_language("de-CH") == "DE"
    assert logic.iso_language("en_GB") == "EN"
    assert logic.iso_language("fr") == "FR"
    assert logic.iso_language(None) == "EN"
    assert logic.iso_language("xyz", "DE") == "DE"


def test_pick_name():
    names = [{"language": "DE", "text": "Herbst"}, {"language": "EN", "text": "Autumn"}]
    assert logic.pick_name(names, "en") == "Autumn"
    assert logic.pick_name(names, "FR") == "Herbst"  # fallback: first entry
    assert logic.pick_name([], "EN") == ""
    assert logic.pick_name(None, "EN") == ""


def test_parse_periods_default_language_is_english():
    assert logic.parse_periods(RAW)[0].name == "Summer break"


def test_parse_periods_kind():
    assert logic.parse_periods(RAW, "DE")[0].kind == logic.KIND_SCHOOL
    public = logic.parse_periods(RAW, "DE", logic.KIND_PUBLIC)
    assert {p.kind for p in public} == {logic.KIND_PUBLIC}
    assert public[0].uid is None
