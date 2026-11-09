# 🎒 School Holidays

> Home Assistant integration that tells you whether **today** or **tomorrow** is a school
> holiday in your country and region, and when the next break begins. Data comes from
> **[OpenHolidays](https://openholidaysapi.org)**, a free community open-data project
> (no API key needed) that covers many countries and their regions.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Validate](https://github.com/Jo-Highness/school_holidays/actions/workflows/validate.yml/badge.svg)](https://github.com/Jo-Highness/school_holidays/actions/workflows/validate.yml)
[![Tests](https://github.com/Jo-Highness/school_holidays/actions/workflows/test.yml/badge.svg)](https://github.com/Jo-Highness/school_holidays/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Jo-Highness/school_holidays)](https://github.com/Jo-Highness/school_holidays/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Home Assistant 2025.2+](https://img.shields.io/badge/Home%20Assistant-2025.2%2B-41BDF5.svg)](https://www.home-assistant.io)

## Quick start

1. **Install** via HACS:
   [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Jo-Highness&repository=school_holidays&category=integration)
   → **Download**, then **restart** Home Assistant.
2. **Add the integration:**
   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=school_holidays)
   → pick your country (e.g. **Germany**) and your region (e.g. **Hesse**).
3. **Done.** You now have a device *Hesse* with these entities (English HA):
   `binary_sensor.hesse_school_holidays_today`, `binary_sensor.hesse_school_holidays_tomorrow`
   and `sensor.hesse_next_school_holiday`. Use them in automations — see the
   [examples](#automation-examples).

> 🇩🇪 Deutschsprachige Kurzanleitung: [siehe unten](#kurzanleitung-deutsch).

---

## Table of contents

- [Why this exists](#why-this-exists)
- [Screenshots](#screenshots)
- [Installation](#installation)
- [Configuration](#configuration)
- [Entities](#entities)
- [Automation examples](#automation-examples)
- [How it behaves](#how-it-behaves)
- [Troubleshooting / FAQ](#troubleshooting--faq)
- [Kurzanleitung (Deutsch)](#kurzanleitung-deutsch)
- [Data source, license and fair use](#data-source-license-and-fair-use)
- [Contributing](#contributing)
- [License](#license)

---

## Why this exists

Plenty of home automations should behave differently on a school holiday: wake-up lights
and alarms, chores, screen-time limits, blinds, heating schedules. Home Assistant has no
built-in source for **school holidays**, and the school-holiday calendar differs by region
(in Germany, for example, every federal state has its own dates).

This integration fills that gap:

- It covers **many countries and their regions** through
  [openholidaysapi.org](https://openholidaysapi.org) — **no API key** required.
  Coverage depends on what the project has published; check that your country/region is
  listed before relying on it.
- Setup is done entirely in the UI. Country and region come from dropdowns that are filled
  live from the API, so there are no ISO codes to memorise and no YAML/REST/template
  scaffolding to maintain.

**How it differs from Workday / public-holiday integrations.** The built-in *Workday*
integration and public-holiday sources model **statutory public holidays and working
days**. School holidays are a different calendar: they are usually multi-week periods, they
vary by region, and a day can be a normal working day for adults while still being a school
holiday. The two complement each other — see [example 3](#3-wake-up-alarm-only-on-real-school-days).

## Screenshots

> Captured from a demo Home Assistant with fictional data.

**Config flow — pick country, then region**

![Config flow: pick the country whose school holidays to track](images/config-flow.png)

**Entities on the device page**

![The integration's entities: today, tomorrow and next school holiday](images/entities.png)

**Example dashboard card**

![Entities card showing today/tomorrow/next school holiday](images/dashboard.png)

## Installation

### HACS (recommended)

1. Click the HACS button in the [Quick start](#quick-start), then choose **Download**.
   Manually: **HACS → ⋮ → Custom repositories**, add
   `https://github.com/Jo-Highness/school_holidays` with type **Integration**, then search
   for *School Holidays* and download it.
2. **Restart** Home Assistant.
3. **Settings → Devices & Services → Add Integration → School Holidays**.

### Manual installation

1. Copy `custom_components/school_holidays/` into your Home Assistant configuration
   directory, so you end up with `<config>/custom_components/school_holidays/`.
2. **Restart** Home Assistant.
3. **Settings → Devices & Services → Add Integration → School Holidays**.

Requires **Home Assistant 2025.2** or newer.

## Configuration

Everything is configured in the UI — there is no YAML.

| Option | Where | Default | Description |
| --- | --- | --- | --- |
| **Country** | Setup, step 1 / **Reconfigure** | — | *Required.* The country whose school-holiday calendar you want. |
| **State / region** | Setup, step 2 / **Reconfigure** | — | *Required when the country has regions.* Skipped automatically for countries without regions (the whole country is used). |
| **Update interval** | **Configure** (options) | `24` hours | How often the API is polled (1–168 h). Holiday dates rarely change; today/tomorrow switch locally at midnight regardless of this value. |
| **Language of holiday names** | **Configure** (options) | *Follow Home Assistant language* | Language used for `holiday_name`. Pick *Follow Home Assistant language*, a listed code, or type any two-letter ISO 639-1 code. Entries created before 1.1.0 keep the language they were set up with until you change it here. |

- **Change country/region later:** **Settings → Devices & Services → School Holidays → ⋮ →
  Reconfigure**. The entry, its entities and their entity IDs are kept.
- **Multiple regions:** add the integration once per country/region. Each entry gets its
  own device (named after the region) and its own entities.
- The UI texts and entity names are translated into English, German, Spanish and French.

## Entities

Each configured region provides the following entities. They use `has_entity_name`, so the
entity ID is built from the **device (region) name + entity name in your Home Assistant
language at the time the entity was created**.

| Entity | Type | Attributes | State |
| --- | --- | --- | --- |
| **School holidays today** | `binary_sensor` | `holiday_name`, `start_date`, `end_date` of the break covering **today** | `on` if today is inside a holiday period |
| **School holidays tomorrow** | `binary_sensor` | `holiday_name`, `start_date`, `end_date` of the break covering **tomorrow** | `on` if tomorrow is inside a holiday period |
| **Next school holiday** | `sensor` (`device_class: date`) | `holiday_name`, `start_date`, `end_date`, `days_until` | Start date of the current or next break, e.g. `2026-10-05` |
| **Last successful update** | `sensor` (`timestamp`, diagnostic) | — | When data was last fetched successfully |
| **Free day today** / **tomorrow** | `binary_sensor` | `name`, `description`, `start_date`, `end_date` of your own free day | `on` if the day is one of the [free days you added](#calendar-and-your-own-free-days) |
| **Day off today** / **tomorrow** | `binary_sensor` | `school_holiday`, `public_holiday`, `free_day` (name of each, or `null`) | `on` if the day is a school holiday, a public holiday **or** one of your free days |
| **School holidays and days off** | `calendar` | — | All school holidays, public holidays and your free days; `on` while one is running |

Notes:

- Outside a holiday, the binary sensors' attributes are `null`. On the last day of a break,
  *today* is `on` (with that break's details) and *tomorrow* is `off` (no details).
- `days_until` is `0` while a break is running. `start_date`/`end_date` are ISO dates and
  both days are part of the break.
- *Next school holiday* has no `state_class` (a date is not a measurement).

**Entity IDs depend on your language.** Examples for the region Hesse/Hessen:

| Entity | English Home Assistant | German Home Assistant |
| --- | --- | --- |
| today | `binary_sensor.hesse_school_holidays_today` | `binary_sensor.hessen_schulferien_heute` |
| tomorrow | `binary_sensor.hesse_school_holidays_tomorrow` | `binary_sensor.hessen_schulferien_morgen` |
| next | `sensor.hesse_next_school_holiday` | `sensor.hessen_nachste_schulferien` |
| last update | `sensor.hesse_last_successful_update` | `sensor.hessen_letzte_erfolgreiche_aktualisierung` |
| free day today | `binary_sensor.hesse_free_day_today` | `binary_sensor.hessen_freier_tag_heute` |
| day off today | `binary_sensor.hesse_day_off_today` | `binary_sensor.hessen_frei_heute` |
| calendar | `calendar.hesse_school_holidays_and_days_off` | `calendar.hessen_ferien_und_freie_tage` |

Check yours under **Settings → Devices & Services → Entities** (search for the region) and
adapt the examples below.

### Calendar and your own free days

The calendar *School holidays and days off* shows, for your region:

- 🎒 **school holidays** and 🎉 **public holidays** from openholidaysapi.org (read-only;
  about half a year back and 13 months ahead), and
- your **own free days**, e.g. movable days off (*bewegliche Ferientage*), bridge days or
  teacher-training days.

To add a free day, open the calendar in the **Calendar** dashboard, click a day (or use
**+ Add event**) and save an all-day event. Single days and date ranges both work;
recurring events are not supported. You can edit or delete your own free days the same
way, but not the holidays that come from the API. Automations can add free days with
`calendar.create_event` (the end date is **exclusive**, as usual in Home Assistant):

```yaml
action: calendar.create_event
target:
  entity_id: calendar.hesse_school_holidays_and_days_off
data:
  summary: Movable day off
  start_date: "2026-11-02"
  end_date: "2026-11-03"
```

Your free days are stored locally in Home Assistant (`.storage`). They are kept when you
reconfigure the region and deleted when you delete the integration entry. They switch on
*Free day today/tomorrow* and *Day off today/tomorrow*. The *School holidays* sensors only
report the official school holidays and are not affected.

## Automation examples

The examples use the English entity IDs for *Hesse*. Replace them with yours.

### 1. Evening notification before the first day off

```yaml
alias: No school tomorrow
triggers:
  - trigger: time
    at: "18:00:00"
conditions:
  - condition: state
    entity_id: binary_sensor.hesse_school_holidays_tomorrow
    state: "on"
  - condition: state
    entity_id: binary_sensor.hesse_school_holidays_today
    state: "off"
actions:
  - action: notify.mobile_app_phone
    data:
      title: "No school tomorrow 🎉"
      message: >-
        {{ state_attr('binary_sensor.hesse_school_holidays_tomorrow', 'holiday_name') }}
        until {{ state_attr('binary_sensor.hesse_school_holidays_tomorrow', 'end_date') }}.
mode: single
```

### 2. Heating schedule: keep the kids' room warm during holidays

```yaml
alias: Kids' room heating on weekday mornings
triggers:
  - trigger: time
    at: "07:45:00"
conditions:
  - condition: time
    weekday: [mon, tue, wed, thu, fri]
actions:
  - if:
      - condition: state
        entity_id: binary_sensor.hesse_school_holidays_today
        state: "on"
    then:
      - action: climate.set_temperature
        target:
          entity_id: climate.kids_room
        data:
          temperature: 21
    else:
      # Kids are at school -> setback temperature.
      - action: climate.set_temperature
        target:
          entity_id: climate.kids_room
        data:
          temperature: 17
mode: single
```

Using the [Scheduler card/component](https://github.com/nielsfaber/scheduler-component)?
Add a condition *`binary_sensor.hesse_school_holidays_today` is off* to your school-day
schedule and a second schedule with *is on* for holidays.

### 3. Wake-up alarm only on real school days

Combine with the built-in [Workday](https://www.home-assistant.io/integrations/workday/)
integration so neither weekends, public holidays nor school holidays wake the kids:

```yaml
alias: School morning wake-up
triggers:
  - trigger: time
    at: "06:45:00"
conditions:
  - condition: state
    entity_id: binary_sensor.workday_sensor
    state: "on"
  - condition: state
    entity_id: binary_sensor.hesse_school_holidays_today
    state: "off"
actions:
  - action: scene.turn_on
    target:
      entity_id: scene.school_wakeup
mode: single
```

### 4. Countdown one week before the next break

```yaml
alias: Holiday countdown
triggers:
  - trigger: time
    at: "07:30:00"
conditions:
  - condition: template
    value_template: >-
      {{ state_attr('sensor.hesse_next_school_holiday', 'days_until') | int(-1) == 7 }}
actions:
  - action: notify.mobile_app_phone
    data:
      message: >-
        One week until {{ state_attr('sensor.hesse_next_school_holiday', 'holiday_name') }}!
mode: single
```

### 5. Template sensor and calendar entry

A template sensor (in `configuration.yaml`) with a readable status text:

```yaml
template:
  - sensor:
      - name: "School holiday status"
        state: >-
          {% set n = 'sensor.hesse_next_school_holiday' %}
          {% if is_state('binary_sensor.hesse_school_holidays_today', 'on') %}
            {{ state_attr('binary_sensor.hesse_school_holidays_today', 'holiday_name') }}
            until {{ state_attr('binary_sensor.hesse_school_holidays_today', 'end_date') }}
          {% elif state_attr(n, 'days_until') is not none %}
            {{ state_attr(n, 'holiday_name') }} in {{ state_attr(n, 'days_until') }} days
          {% else %}
            No upcoming school holidays known
          {% endif %}
```

The integration has its [own calendar](#calendar-and-your-own-free-days). If you also want
the breaks in another calendar, you can copy each upcoming break into a [Local Calendar](https://www.home-assistant.io/integrations/local_calendar/) (all-day
events in Home Assistant use an **exclusive** end date, hence the `+ 1 day`):

```yaml
alias: Copy next school holiday to the family calendar
triggers:
  - trigger: state
    entity_id: sensor.hesse_next_school_holiday
    not_from: ["unknown", "unavailable"]
    not_to: ["unknown", "unavailable"]
actions:
  - action: calendar.create_event
    target:
      entity_id: calendar.family
    data:
      summary: "{{ state_attr('sensor.hesse_next_school_holiday', 'holiday_name') }}"
      start_date: "{{ state_attr('sensor.hesse_next_school_holiday', 'start_date') }}"
      end_date: >-
        {{ (strptime(state_attr('sensor.hesse_next_school_holiday', 'end_date'), '%Y-%m-%d')
            + timedelta(days=1)).strftime('%Y-%m-%d') }}
mode: queued
```

## How it behaves

- **Polling + local midnight rollover.** Holiday periods for the next ~400 days are fetched
  once per update interval (default 24 h). Shortly after local midnight, *today*,
  *tomorrow* and *next* are **recomputed locally without a network call**, so they switch
  exactly at the day boundary.
- **Robust against API outages.** If a refresh fails, the integration **keeps its last
  known data** instead of going `unavailable`. Because the cached window covers more than a
  year ahead, the sensors stay correct.
- **Repair notice for long outages.** If no refresh has succeeded for **7 days**, a repair
  issue appears under **Settings → System → Repairs**. It disappears automatically after
  the next successful update. *Last successful update* shows the timestamp.
- **Clean first setup.** If the **very first** fetch fails, setup is retried by Home
  Assistant (`ConfigEntryNotReady`) instead of creating empty sensors.
- **Language changes.** With *Follow Home Assistant language*, holiday names are re-fetched
  when you change the Home Assistant language.
- **Public holidays are best effort.** They are fetched together with the school holidays.
  If only that request fails, the previously loaded public holidays are kept and the
  school-holiday sensors are not affected.

## Troubleshooting / FAQ

**The entry keeps retrying after adding it.**
openholidaysapi.org could not be reached during the first setup. Home Assistant retries
automatically. Check that your host can reach `openholidaysapi.org` over HTTPS.

**I picked the wrong country or region.**
Use **⋮ → Reconfigure** on the integration entry. Entity IDs stay the same, so existing
automations keep working (the device is renamed to the new region; rename entity IDs
yourself if you want them to match).

**My entity IDs look different from the examples.**
They are generated from your Home Assistant language and region name — see
[Entities](#entities).

**Holiday names are in the wrong language.**
Set **Configure → Language of holiday names**. If OpenHolidays has no name in that
language, another available name is used.

**Download diagnostics** via **⋮ → Download diagnostics** when reporting a bug, and
enable debug logging if needed:

```yaml
logger:
  logs:
    custom_components.school_holidays: debug
```

## Kurzanleitung (Deutsch)

Die Integration liefert pro Bundesland/Region, ob **heute** oder **morgen** Schulferien sind
und wann die **nächsten Ferien** beginnen. Daten: [OpenHolidays](https://openholidaysapi.org)
(freies Open-Data-Projekt, kein API-Key).

1. **Installieren:** In HACS dieses Repository öffnen (Button oben) → **Herunterladen** →
   Home Assistant **neu starten**.
2. **Einrichten:** **Einstellungen → Geräte & Dienste → Integration hinzufügen →
   School Holidays** → Land **Deutschland**, Region z. B. **Hessen** wählen.
3. **Nutzen:** Bei deutscher Home-Assistant-Sprache entstehen
   `binary_sensor.hessen_schulferien_heute`, `binary_sensor.hessen_schulferien_morgen` und
   `sensor.hessen_nachste_schulferien` (Attribute `holiday_name`, `start_date`, `end_date`,
   `days_until`). Die Beispiele oben verwenden englische IDs (`hesse_…`) — bitte anpassen.

**Kalender und eigene freie Tage:** Der Kalender `calendar.hessen_ferien_und_freie_tage`
zeigt Schulferien 🎒, Feiertage 🎉 und deine eigenen freien Tage. Eigene freie Tage (z. B.
bewegliche Ferientage oder Brückentage) legst du im **Kalender**-Dashboard als ganztägigen
Termin an; nur diese lassen sich bearbeiten oder löschen. Dazu gibt es:

- `binary_sensor.hessen_freier_tag_heute` / `_morgen`: `on` an deinen eigenen freien Tagen.
- `binary_sensor.hessen_frei_heute` / `_morgen`: `on` bei Schulferien, Feiertag **oder**
  eigenem freien Tag. Die Attribute `school_holiday`, `public_holiday` und `free_day`
  zeigen, warum der Tag frei ist.

Die Schulferien-Sensoren bleiben davon unberührt.

Weitere Hinweise:

- **Konfigurieren:** Aktualisierungsintervall (Standard 24 h) und Sprache der Feriennamen
  (Standard: Home-Assistant-Sprache).
- **Falsches Bundesland?** **⋮ → Neu konfigurieren** — Entitäten und IDs bleiben erhalten.
- Bei API-Ausfall bleiben die letzten Daten aktiv; nach 7 Tagen ohne Aktualisierung
  erscheint ein Hinweis unter **Einstellungen → System → Reparaturen**.

Beispiel: Wecker nur an echten Schultagen (zusammen mit der Integration *Workday*/Arbeitstag):

```yaml
alias: Schulwecker
triggers:
  - trigger: time
    at: "06:45:00"
conditions:
  - condition: state
    entity_id: binary_sensor.workday_sensor
    state: "on"
  - condition: state
    entity_id: binary_sensor.hessen_schulferien_heute
    state: "off"
actions:
  - action: scene.turn_on
    target:
      entity_id: scene.schulwecker
mode: single
```

## Data source, license and fair use

- Holiday data: **[OpenHolidays API](https://openholidaysapi.org)**, an open-data project
  by STÜBER SYSTEMS GmbH. The data is published under the
  [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
  ([data repository](https://github.com/openpotato/openholidaysapi.data)). It is a
  community project, not an official government source — verify important dates with your
  school or education ministry.
- This integration is **not affiliated** with the OpenHolidays project.
- **Fair use:** the service is free and has no API key. The integration makes one small
  request per region per update interval (default once a day) plus a few requests during
  setup. Please don't lower the interval without need.

## Contributing

Contributions are welcome — bug reports, feature ideas, translations and pull requests. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for the development setup, and open an issue on the
[issue tracker](https://github.com/Jo-Highness/school_holidays/issues) first for larger
changes.

## License

Released under the **MIT** license. See [`LICENSE`](LICENSE). Built for
**[Home Assistant](https://www.home-assistant.io)**.
