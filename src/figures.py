"""Charts for the application (PNG, light theme): figures/*.png.

Palette: first three slots of a color-blind-safe categorical palette; thin lines, legend + labels, muted grid.
Input: figures/metrics.json, data/clean/test_predictions.csv (model.py), figures/savings_summary.json (export.py).
Run: .venv/bin/python src/figures.py
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

import simulate as sim  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"  # blue, orange, aqua: the first three slots pass every pair check

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "legend.frameon": False, "lines.linewidth": 2, "axes.axisbelow": True, "axes.titlepad": 26,
})


def _legend_on_top(ax, ncol: int = 3) -> None:
    """Legend between the title and the plot so it never covers the data."""
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=ncol, fontsize=9, borderaxespad=0.3)


def _save(fig, name: str, source: str, source_y: float = -0.01) -> None:
    fig.text(0.01, source_y, source, fontsize=7.5, color=INK2, ha="left", va="top")
    fig.savefig(FIG / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"-> figures/{name}")


def forecast_example(preds: pd.DataFrame) -> None:
    """One test week in one room: measured, LightGBM and no-change baseline, 3 hours ahead."""
    d = preds[(preds.horizon == 3) & (preds.house == "Use1001") & (preds.room == "living")].copy()
    d["target_time"] = pd.to_datetime(d["time"]) + pd.Timedelta(hours=3)
    d = d.set_index("target_time").sort_index()
    weekly_range = d["actual"].resample("7D").agg(lambda s: s.max() - s.min())
    start = weekly_range.idxmax()
    w = d.loc[start:start + pd.Timedelta(days=7)]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.plot(w.index, w["actual"], color=S1, label="Measured")
    ax.plot(w.index, w["lightgbm"], color=S2, label="LightGBM, 3 h ahead")
    ax.plot(w.index, w["persistence"], color=S3, linewidth=1.5, label="No-change baseline, 3 h ahead")
    ax.set_ylabel("Room temperature, °C")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_title("3-hour forecast vs measurement (ThermBuild living room, test period)")
    _legend_on_top(ax)
    _save(fig, "forecast_example.png", "Data: ThermBuild (Fraunhofer, CC BY-SA 4.0), house Use1001. Model trained on data before 2026-01-01.")


def model_mae(metrics: dict) -> None:
    models = [("persistence", "No-change baseline", S3), ("ridge", "Linear (Ridge)", S1), ("lightgbm", "LightGBM", S2)]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    width = 0.26
    for k, (key, label, color) in enumerate(models):
        xs = [i + (k - 1) * width for i in range(2)]
        vals = [metrics[h]["mae_c"][key] for h in ("h1", "h3")]
        bars = ax.bar(xs, vals, width, color=color, label=label, edgecolor=SURFACE, linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.006, f"{v:.2f}", ha="center", va="bottom", fontsize=9, color=INK)
    ax.set_xticks([0, 1], ["1 hour ahead", "3 hours ahead"])
    ax.set_ylabel("Mean absolute error, °C")
    ax.grid(axis="x", visible=False)
    n = metrics["h1"]["n_test"]
    ax.set_ylim(0, max(metrics["h3"]["mae_c"].values()) * 1.15)
    ax.set_title("Forecast error on unseen data (lower is better)")
    _legend_on_top(ax)
    _save(fig, "model_mae.png", f"Test: 2026-02-01..2026-04-25, 14 rooms, {n:,} room-hours. Data: ThermBuild (CC BY-SA 4.0).")


NICE = {"dT_1h": "Change over last 1 h", "dT_3h": "Change over last 3 h", "hour": "Hour of day",
        "room_id": "Room", "t_air": "Temperature now", "t_air_lag1": "Temperature 1 h ago",
        "t_supply": "Heating supply temperature", "solar_future": "Solar radiation (forecast)",
        "solar": "Solar radiation now", "t_out_future": "Outdoor temperature (forecast)",
        "valve_mean12": "Valve opening, last 12 h", "valve_mean3": "Valve opening, last 3 h",
        "t_out_mean24": "Outdoor temperature, last 24 h", "t_air_lag24": "Temperature 24 h ago",
        "t_in_minus_out": "Indoor minus outdoor", "t_air_lag12": "Temperature 12 h ago",
        "t_air_lag2": "Temperature 2 h ago", "t_air_lag3": "Temperature 3 h ago", "t_air_lag6": "Temperature 6 h ago",
        "valve": "Valve opening now", "valve_lag1": "Valve opening 1 h ago", "t_out": "Outdoor temperature now",
        "heat_on": "Heating mode on", "dow": "Day of week"}


def feature_importance(metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharex=True)
    for ax, h, title in zip(axes, ("h1", "h3"), ("1 hour ahead", "3 hours ahead")):
        top = list(metrics[h]["feature_gain_share"].items())[:8][::-1]
        ax.barh([NICE.get(k, k) for k, _ in top], [v * 100 for _, v in top], color=S1, edgecolor=SURFACE, linewidth=2)
        for i, (_, v) in enumerate(top):
            ax.text(v * 100 + 0.5, i, f"{v * 100:.0f}%", va="center", fontsize=8.5, color=INK)
        ax.set_title(title, fontsize=11)
        ax.grid(axis="y", visible=False)
        ax.set_xlabel("Share of total gain, %")
    fig.suptitle("What the LightGBM forecast relies on (top 8 features)", x=0.01, ha="left",
                 fontsize=12, fontweight="semibold")
    fig.tight_layout()
    _save(fig, "feature_importance.png", "Gain-based importance, LightGBM trained on ThermBuild measurements.")


def savings_room_temp(noise: float) -> None:
    """Two weeks of the Astana season: the room without the system and with SmartHeat."""
    times, weather = sim.season_weather("Astana")
    p, curve = sim.RoomParams(), sim.CITIES["Astana"]
    base = sim.run_baseline(p, curve, weather)
    smart = sim.run_smart(p, curve, weather, sim.physics_predictor(p, curve, noise_std=noise))
    t15 = pd.date_range(times[0], periods=len(base.temps), freq="15min")
    df = pd.DataFrame({"without": base.temps, "smart": smart.temps}, index=t15)
    over = (df["without"] > 24).resample("14D").sum()
    start = over.idxmax()
    w = df.loc[start:start + pd.Timedelta(days=14)]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.axhspan(sim_t_min := 21.0, 22.0, color=S1, alpha=0.08, linewidth=0)
    ax.axhline(24.0, color=INK2, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(w.index[0], 24.08, "Overheating 24 °C", fontsize=8.5, color=INK2, va="bottom")
    ax.text(w.index[0], sim_t_min + 0.05, "Target 21-22 °C", fontsize=8.5, color=INK2, va="bottom")
    ax.plot(w.index, w["without"], color=S2, linewidth=1.6, label="Without system (valve open, window to cool down)")
    ax.plot(w.index, w["smart"], color=S1, label="With SmartHeat (valve follows 1-hour forecast)")
    ax.set_ylabel("Room temperature, °C")
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_title("Simulated room in Astana, real weather of the 2025/26 season")
    _legend_on_top(ax, ncol=2)
    _save(fig, "savings_room_temp.png", "RC room model; weather: Open-Meteo (CC BY 4.0). Assumptions: SOURCES.md / savings_summary.json.")


def savings_by_city(summary: dict) -> None:
    cities = list(summary["cities"])[::-1]  # Astana (the headline number) on top
    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    for i, c in enumerate(cities):
        s = summary["cities"][c]
        lo, b, hi = s["low"]["saved_pct"], s["base"]["saved_pct"], s["high"]["saved_pct"]
        ax.barh(i, b, color=S1, height=0.5, edgecolor=SURFACE, linewidth=2)
        ax.errorbar(b, i, xerr=[[b - lo], [hi - b]], color=INK, capsize=4, linewidth=1.2)
        ax.text(hi + 1.5, i, f"{b:.0f}% (range {lo:.0f}-{hi:.0f}%)\n{s['base']['saved_kwh']:.0f} kWh per room, "
                f"{s['days']} days", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(range(len(cities)), cities)
    ax.set_xlim(0, 85)
    ax.set_xlabel("Heat saved vs no system, %")
    ax.grid(axis="y", visible=False)
    ax.set_title("Simulated heat savings per room, 2025/26 heating season")
    _save(fig, "savings_by_city.png", "Range: cautious / base / bold assumptions. Baku design temperature is an assumption.",
          source_y=-0.07)


def main() -> None:
    metrics = json.loads((FIG / "metrics.json").read_text())
    summary = json.loads((FIG / "savings_summary.json").read_text())
    preds = pd.read_csv(ROOT / "data" / "clean" / "test_predictions.csv", parse_dates=["time"])
    forecast_example(preds)
    model_mae(metrics)
    feature_importance(metrics)
    savings_room_temp(summary["forecast_noise_std_c"])
    savings_by_city(summary)


if __name__ == "__main__":
    main()
