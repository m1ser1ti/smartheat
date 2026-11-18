"""Open-Meteo weather (Historical Weather API, no key) for Astana and Baku.

Source and license: SOURCES.md. Output: data/raw/weather_<city>.csv (time, t_out), local time.
Run: .venv/bin/python src/weather.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://archive-api.open-meteo.com/v1/archive"

CITIES = {
    "Astana": {"latitude": 51.1694, "longitude": 71.4491, "timezone": "Asia/Almaty"},
    "Baku": {"latitude": 40.4093, "longitude": 49.8671, "timezone": "Asia/Baku"},
}
# All of last winter; the heating season is cut out later by the city threshold rule (simulate.heating_season).
START, END = "2025-09-01", "2026-05-31"


def fetch(city: str) -> Path:
    import requests

    params = {**CITIES[city], "start_date": START, "end_date": END, "hourly": "temperature_2m"}
    r = requests.get(API, params=params, timeout=60)
    r.raise_for_status()
    hourly = r.json()["hourly"]
    rows = [(t, v) for t, v in zip(hourly["time"], hourly["temperature_2m"]) if v is not None]
    out = ROOT / "data" / "raw" / f"weather_{city.lower()}.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time", "t_out"])
        w.writerows(rows)
    missing = len(hourly["time"]) - len(rows)
    print(f"{city}: {len(rows)} hours, {missing} missing, {min(v for _, v in rows):.1f}..{max(v for _, v in rows):.1f} °C -> {out.relative_to(ROOT)}")
    return out


def load(city: str) -> list[tuple[str, float]]:
    """Hourly [(ISO time, t_out °C)]. Standard library only."""
    path = ROOT / "data" / "raw" / f"weather_{city.lower()}.csv"
    with path.open() as f:
        return [(row["time"], float(row["t_out"])) for row in csv.DictReader(f)]


if __name__ == "__main__":
    for c in CITIES:
        fetch(c)
