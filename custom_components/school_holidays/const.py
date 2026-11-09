"""Constants for the School Holidays integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "school_holidays"

CONF_COUNTRY = "country"
CONF_SUBDIVISION = "subdivision"
CONF_COUNTRY_NAME = "country_name"
CONF_SUBDIVISION_NAME = "subdivision_name"
CONF_LANGUAGE = "language"
CONF_UPDATE_HOURS = "update_hours"

# Language value meaning "follow the Home Assistant language" (default for new
# entries since 1.1.0). Entries created before 1.1.0 keep their explicit code.
LANGUAGE_AUTO = "auto"
DEFAULT_LANGUAGE = "EN"
# Offered in the options flow; any other ISO 639-1 code can be typed in.
LANGUAGE_CHOICES = ["EN", "DE", "FR", "ES", "IT", "NL", "PL", "PT", "CS", "SK", "HU", "RO"]

DEFAULT_UPDATE_HOURS = 24
MIN_UPDATE_HOURS = 1
MAX_UPDATE_HOURS = 168
# How far ahead to fetch holiday periods (covers a full school year + buffer).
LOOKAHEAD_DAYS = 400
# How far back to fetch, so the calendar also shows the recent past. Together with
# LOOKAHEAD_DAYS this stays well below the API's maximum window of three years.
LOOKBACK_DAYS = 180
# After this long without a successful refresh a repair issue is raised. The
# cached periods are still used, because they cover the next ~13 months.
STALE_AFTER = timedelta(days=7)
ISSUE_STALE_DATA = "stale_data"

# Coordinator data keys.
DATA_PERIODS = "periods"
DATA_TODAY = "today"
DATA_TOMORROW = "tomorrow"
DATA_CURRENT = "current"  # period covering today: dict name/start/end or None
DATA_TOMORROW_PERIOD = "tomorrow_period"  # period covering tomorrow or None
DATA_NEXT = "next"  # dict name/start/end/days_until or None
DATA_LAST_SUCCESS = "last_successful_update"  # aware datetime or None
DATA_FREE_TODAY = "free_day_today"  # user-defined free day covering today or None
DATA_FREE_TOMORROW = "free_day_tomorrow"  # user-defined free day covering tomorrow or None
DATA_DAY_OFF_TODAY = "day_off_today"  # dict on/school_holiday/public_holiday/free_day
DATA_DAY_OFF_TOMORROW = "day_off_tomorrow"
DATA_PUBLIC_HOLIDAYS = "public_holidays"  # number of public holidays loaded
DATA_FREE_DAYS = "free_days"  # number of user-defined free days

# Storage of the user-defined free days (one file per config entry).
STORAGE_VERSION = 1
