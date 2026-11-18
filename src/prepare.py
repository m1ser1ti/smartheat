"""ThermBuild cleaning: real measurements of two houses -> hourly table per room.

Input:  data/raw/thermbuild/*_imputed.csv (15-minute step, 2 houses x 7 rooms)
Output: data/clean/rooms_hourly.csv
        time, house, room, t_air, valve, win, t_out, solar, t_supply, heat_on

Decisions:
- Time: TIME is a row number; the first day is partial, so the start is 7 February 2025
  (day_of_the_year=38, non-leap year, year rolls over after day 365) plus the first-day offset.
- Outliers: t_air outside 10..35 °C and jumps above 2 °C in 15 min are treated as sensor faults.
- Heating months only (October-April).
- An hour is the mean of four 15-minute values if at least three are present.
Run: .venv/bin/python src/prepare.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "thermbuild"
OUT = ROOT / "data" / "clean" / "rooms_hourly.csv"

START_DAY = pd.Timestamp("2025-02-07")  # day_of_the_year 38 in non-leap 2025
HEATING_MONTHS = {10, 11, 12, 1, 2, 3, 4}
T_MIN, T_MAX, MAX_JUMP = 10.0, 35.0, 2.0


def load_house(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    house = path.name.split("_")[1]  # Use1001 / Use1002
    first_day_rows = int((df["consecutive_days"] == df["consecutive_days"].min()).sum())
    start = START_DAY + pd.Timedelta(minutes=15 * (96 - first_day_rows))
    df["time"] = start + pd.to_timedelta(df["TIME"] * 15, unit="min")
    if df["time"].diff().dropna().ne(pd.Timedelta(minutes=15)).any():
        raise ValueError(f"{path.name}: time step is not 15 min")

    rooms = sorted({c.rsplit("_", 1)[0] for c in df.columns if c.startswith("room_")})
    shared = pd.DataFrame({
        "time": df["time"],
        "t_out": df["wea_Tair_out"],
        "solar": df["wea_IbeamHor"].fillna(0) + df["wea_IdiffHor"].fillna(0),
        "t_supply": df["dist_Tflow_store_ufh"],
        "heat_on": df["mode_heat"],
    })
    parts = []
    for r in rooms:
        part = shared.copy()
        part["house"] = house
        part["room"] = r.split("_", 2)[2]  # child1, sleep, living...
        part["t_air"] = df[f"{r}_Tair"]
        part["valve"] = df[f"{r}_valve"]
        part["win"] = df[f"{r}_win"]
        parts.append(part)
    return pd.concat(parts, ignore_index=True)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {"rows_15min": len(df)}
    bad_range = ~df["t_air"].between(T_MIN, T_MAX)
    jump = df.groupby(["house", "room"])["t_air"].diff().abs() > MAX_JUMP
    stats["outliers_range"] = int(bad_range.sum())
    stats["outliers_jump"] = int((jump & ~bad_range).sum())
    df.loc[bad_range | jump, "t_air"] = np.nan

    df = df[df["time"].dt.month.isin(HEATING_MONTHS)]
    df = df.assign(hour=df["time"].dt.floor("h"))
    agg = {c: "mean" for c in ["t_air", "valve", "win", "t_out", "solar", "t_supply", "heat_on"]}
    hourly = df.groupby(["house", "room", "hour"]).agg(agg)
    counts = df.groupby(["house", "room", "hour"])["t_air"].count()
    hourly.loc[counts < 3, "t_air"] = np.nan
    hourly = hourly.reset_index().rename(columns={"hour": "time"})
    stats["hours"] = len(hourly)
    stats["hours_missing_t_air"] = int(hourly["t_air"].isna().sum())
    return hourly, stats


def load_clean() -> pd.DataFrame:
    return pd.read_csv(OUT, parse_dates=["time"])


def main() -> None:
    files = sorted(RAW.glob("*_imputed.csv"))
    if not files:
        raise SystemExit("no data/raw/thermbuild/*_imputed.csv: download ThermBuild_measure_imputed.zip (see SOURCES.md)")
    raw = pd.concat([load_house(f) for f in files], ignore_index=True)
    hourly, stats = clean(raw)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(OUT, index=False, float_format="%.4f")
    print(stats)
    print(f"period {hourly.time.min()} .. {hourly.time.max()}, window ever open: {(hourly.win > 0).any()}")
    print(hourly.groupby(["house", "room"]).agg(hours=("t_air", "count"), t_mean=("t_air", "mean"),
                                                t_max=("t_air", "max"), valve_mean=("valve", "mean")).round(2))
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
