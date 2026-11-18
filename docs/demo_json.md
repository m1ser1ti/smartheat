# demo.json format (schema_version 1)

The single data source for the app. Written by `src/export.py`, read by `ios/SmartHeat/SmartHeat/Models.swift`.
The file lives at `ios/SmartHeat/SmartHeat/demo.json` and is bundled into the app at build time.
If a field changes, update both files and `schema_version`.

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | int | 1 |
| `generated_at` | ISO 8601 string (UTC) | when the file was built |
| `synthetic` | bool | `true` = synthetic data; the app shows a "Synthetic data" banner. Only `false` goes into the application |
| `notes` | [string] | notes for the team; the first one is shown on the Room screen |
| `room.name`, `room.city` | string | labels on the Room screen |
| `room.temp_now`, `room.temp_outside` | number, °C | |
| `room.target_min`, `room.target_max` | number, °C | comfort band (21-22) |
| `room.overheat_threshold` | number, °C | overheating threshold (24) |
| `room.window_open` | bool | |
| `room.valve` | number 0-1 | current valve opening |
| `forecast.model` | string | data source shown under the chart |
| `forecast.step_minutes` | int | 15 |
| `forecast.mae_hour1_c`, `forecast.mae_hour3_c` | number or `null` | model error, °C. Do not rename to `mae_1h_c`: Swift cannot decode that key |
| `forecast.points[]` | `{minutes, temp, temp_with_system}` | 0..180 min; `temp` without action, `temp_with_system` with the smart valve |
| `alert.overheat_in_minutes` | int or `null` | minutes until overheating without action |
| `alert.title`, `alert.body` | string, `body` may be `null` | local notification text |
| `advice[]` | `{id, severity: info/warning, title, text}` | advice, 3-6 items |
| `savings[]` | see below | per city |
| `assumptions` | [string] | simulation assumptions, shown in small print |

`savings[]`:

| Field | Type | Meaning |
|---|---|---|
| `city` | string | Astana, Baku |
| `period_days` | int | length of the period |
| `scope` | string | `room`: numbers are per room |
| `building_rooms` | int | multiplier for the building (100) |
| `kwh`, `percent` | `{low, base, high}` | heat saved: cautious / base / bold |
| `money` | `{currency, low, base, high}` or `null` | `null` until tariffs arrive |
| `co2_kg` | `{low, base, high}` or `null` | `null` without an emission factor |
| `hours_above_24` | `{baseline, smart}` | overheating hours without and with the system |
