"""RC model of a room with district heating: two scenarios and the savings estimate.

Standard library only: runs without pandas or numpy.

Scenarios:
- baseline: the radiator valve is always open (typical riser without control),
  the occupant opens the window above 24 °C and closes it below 22 °C;
- smart: the window stays closed (the app's advice is followed) and the smart valve picks
  the largest opening for which the 1-hour temperature FORECAST stays at or below 22 °C.
  The forecast comes from a predictor function: a physics predictor (the same RC model)
  with the forecast error measured for LightGBM on ThermBuild.

All default numbers are assumptions (see ASSUMPTIONS below) and must be backed by
sources before the application.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Sequence

DT_S = 900  # 15-minute integration step, same as ThermBuild
STEPS_PER_HOUR = 3600 // DT_S
VALVE_LEVELS = (1.0, 0.75, 0.5, 0.25, 0.0)


@dataclass(frozen=True)
class RoomParams:
    """A ~20 m² room in a panel building. All values are assumptions."""

    ua_envelope: float = 25.0      # W/K: external wall + window
    ua_infiltration: float = 9.0   # W/K: 0.5 air changes per hour in 54 m³
    ua_window_open: float = 60.0   # W/K: extra loss when the window is open
    capacity: float = 3.0e6        # J/K: air + internal walls and furniture
    k_radiator: float = 26.0       # W/K with the valve open: ~22 °C at the design outdoor temperature, no oversizing
    radiator_drop: float = 10.0    # K: mean radiator temperature below the supply temperature
    internal_gains: float = 150.0  # W: people and appliances

    def ua_closed(self) -> float:
        return self.ua_envelope + self.ua_infiltration


@dataclass(frozen=True)
class HeatingCurve:
    """Supply temperature curve with an upper cap and a lower break point.

    The break point (supply never below t_supply_min in mild weather) is what causes overheating.
    """

    t_out_design: float            # design outdoor temperature of the city
    t_supply_design: float = 95.0
    t_out_end: float = 8.0         # end of the heating season
    t_supply_end: float = 40.0
    t_supply_min: float = 60.0     # break point of the curve

    def supply(self, t_out: float) -> float:
        span = self.t_out_end - self.t_out_design
        frac = (t_out - self.t_out_design) / span
        linear = self.t_supply_design + frac * (self.t_supply_end - self.t_supply_design)
        return min(self.t_supply_design, max(self.t_supply_min, linear))


CITIES = {
    # Astana: -31.2 °C, coldest five-day period (design documentation, SOURCES.md).
    # Baku: -4 °C is an assumption without a source; sensitivity is printed by running this module.
    "Astana": HeatingCurve(t_out_design=-31.2),
    "Baku": HeatingCurve(t_out_design=-4.0),
}

# Heating season: daily mean temperature at or below the threshold for 5 days in a row.
# Astana: +10 °C (city rule, SOURCES.md); Baku: +8 °C (assumption, SNiP rule).
SEASON_THRESHOLD = {"Astana": 10.0, "Baku": 8.0}

ASSUMPTIONS = [
    "Room ~20 m2 in a panel building, envelope UA 25 W/K, infiltration 9 W/K",
    "Radiator sized to hold ~22 C at the design outdoor temperature (Astana -31.2 C, Baku -4 C)",
    "Supply curve 95 C at design temperature, 40 C at +8 C, never below 60 C in mild weather (range 55-65)",
    "Open window adds 60 W/K (range 30-90)",
    "Without system: valve always open, window opened above 24 C, closed below 22 C",
    "With SmartHeat: window kept closed, valve throttled when the 1-hour forecast exceeds 22 C",
    "Forecast error equals the LightGBM 1-hour error measured on ThermBuild test data",
    "Heating season: 5-day mean outdoor temperature at or below +10 C (Astana) / +8 C (Baku)",
]


def radiator_power(p: RoomParams, curve: HeatingCurve, t_out: float, t_in: float, valve: float) -> float:
    t_rad = curve.supply(t_out) - p.radiator_drop
    return valve * p.k_radiator * max(0.0, t_rad - t_in)


def step(p: RoomParams, curve: HeatingCurve, t_in: float, t_out: float, valve: float, window: bool) -> tuple[float, float]:
    """One 15-minute step (explicit Euler). Returns (new temperature, radiator power in W)."""
    ua = p.ua_closed() + (p.ua_window_open if window else 0.0)
    q_rad = radiator_power(p, curve, t_out, t_in, valve)
    dT = (q_rad + p.internal_gains - ua * (t_in - t_out)) * DT_S / p.capacity
    return t_in + dT, q_rad


Predictor = Callable[[float, float, float], float]
"""(indoor temperature now, outdoor temperature, valve opening) -> forecast temperature in 1 hour."""


def physics_predictor(p: RoomParams, curve: HeatingCurve, bias: float = 0.0,
                      noise_std: float = 0.0, seed: int = 0) -> Predictor:
    """Forecast with the same RC model plus error: a bias and random noise with std noise_std.

    noise_std comes from the LightGBM error on ThermBuild test data (figures/metrics.json),
    so the valve control makes mistakes as often as the real model would.
    """
    import random

    rng = random.Random(seed)

    def predict(t_in: float, t_out: float, valve: float) -> float:
        t = t_in
        for _ in range(STEPS_PER_HOUR):
            t, _ = step(p, curve, t, t_out, valve, window=False)
        return t + bias + (rng.gauss(0.0, noise_std) if noise_std else 0.0)

    return predict


def thermostat_predictor() -> Predictor:
    """A "forecast" without a model: in one hour it will be the same as now. With it the smart
    scenario becomes a plain thermostat (close the valve once it is already above 22 °C).
    Used to measure what the forecast adds."""
    return lambda t_in, t_out, valve: t_in


@dataclass
class RunResult:
    energy_kwh: float
    temps: list[float]
    valves: list[float]
    windows: list[bool]

    def hours_above(self, threshold: float) -> float:
        return sum(1 for t in self.temps if t > threshold) / STEPS_PER_HOUR

    def hours_below(self, threshold: float) -> float:
        return sum(1 for t in self.temps if t < threshold) / STEPS_PER_HOUR

    def window_hours(self) -> float:
        return sum(self.windows) / STEPS_PER_HOUR

    def mean_temp(self) -> float:
        return sum(self.temps) / len(self.temps)


def _expand(hourly: Sequence[float]) -> list[float]:
    return [t for t in hourly for _ in range(STEPS_PER_HOUR)]


def run_baseline(p: RoomParams, curve: HeatingCurve, weather_hourly: Sequence[float],
                 t0: float = 21.0, open_above: float = 24.0, close_below: float = 22.0) -> RunResult:
    t, window, energy = t0, False, 0.0
    temps, valves, windows = [], [], []
    for t_out in _expand(weather_hourly):
        if not window and t > open_above:
            window = True
        elif window and t < close_below:
            window = False
        t, q = step(p, curve, t, t_out, 1.0, window)
        energy += q * DT_S
        temps.append(t); valves.append(1.0); windows.append(window)
    return RunResult(energy / 3.6e6, temps, valves, windows)


def run_smart(p: RoomParams, curve: HeatingCurve, weather_hourly: Sequence[float],
              predictor: Predictor | None = None, t0: float = 21.0, target_max: float = 22.0) -> RunResult:
    predictor = predictor or physics_predictor(p, curve)
    t, energy = t0, 0.0
    temps, valves, windows = [], [], []
    for t_out in _expand(weather_hourly):
        valve = next((v for v in VALVE_LEVELS if predictor(t, t_out, v) <= target_max), 0.0)
        t, q = step(p, curve, t, t_out, valve, window=False)
        energy += q * DT_S
        temps.append(t); valves.append(valve); windows.append(False)
    return RunResult(energy / 3.6e6, temps, valves, windows)


@dataclass
class Savings:
    baseline: RunResult
    smart: RunResult

    @property
    def saved_kwh(self) -> float:
        return self.baseline.energy_kwh - self.smart.energy_kwh

    @property
    def saved_pct(self) -> float:
        return 100.0 * self.saved_kwh / self.baseline.energy_kwh if self.baseline.energy_kwh else 0.0


def compare(p: RoomParams, curve: HeatingCurve, weather_hourly: Sequence[float],
            predictor: Predictor | None = None) -> Savings:
    return Savings(run_baseline(p, curve, weather_hourly), run_smart(p, curve, weather_hourly, predictor))


def savings_range(curve: HeatingCurve, weather_hourly: Sequence[float],
                  base: RoomParams = RoomParams(), noise_std: float = 0.0, seed: int = 0) -> dict[str, Savings]:
    """Savings under cautious, base and bold assumptions (the range quoted in the application)."""
    variants = {
        "low": (replace(base, ua_window_open=30.0), replace(curve, t_supply_min=55.0)),
        "base": (base, curve),
        "high": (replace(base, ua_window_open=90.0), replace(curve, t_supply_min=65.0)),
    }
    return {name: compare(p, c, weather_hourly, physics_predictor(p, c, noise_std=noise_std, seed=seed))
            for name, (p, c) in variants.items()}


def heating_season(times: Sequence[str], temps: Sequence[float], threshold: float) -> tuple[int, int]:
    """Hour indices [start, end) of the heating season.

    Start: the first day of the first 5-day run with daily mean temperature at or below the threshold.
    End: the last day of the last such run (in spring). Times are ISO strings 'YYYY-MM-DDTHH:MM'.
    """
    days: dict[str, list[float]] = {}
    for t, v in zip(times, temps):
        days.setdefault(t[:10], []).append(v)
    dates = sorted(days)
    means = [sum(days[d]) / len(days[d]) for d in dates]
    cold = [all(m <= threshold for m in means[i:i + 5]) for i in range(len(means) - 4)]
    if not any(cold):
        raise ValueError("no heating season for this threshold")
    first = cold.index(True)
    last = len(cold) - 1 - cold[::-1].index(True) + 4  # last day of the last cold 5-day run
    start_day, end_day = dates[first], dates[last]
    start = next(i for i, t in enumerate(times) if t[:10] == start_day)
    end = max(i for i, t in enumerate(times) if t[:10] == end_day) + 1
    return start, end


def synthetic_weather(days: int = 30, start: float = -20.0, end: float = 5.0, daily_amp: float = 4.0) -> list[float]:
    """Synthetic weather for tests and the stub: linear trend + daily cycle. NOT for the application."""
    import math

    n = days * 24
    return [start + (end - start) * i / max(1, n - 1) + daily_amp * math.sin(2 * math.pi * (i % 24 - 9) / 24)
            for i in range(n)]


def season_weather(city: str) -> tuple[list[str], list[float]]:
    """Hourly Open-Meteo weather for the city's heating season (data/raw/weather_<city>.csv)."""
    from weather import load

    rows = load(city)
    times, temps = [t for t, _ in rows], [v for _, v in rows]
    s, e = heating_season(times, temps, SEASON_THRESHOLD[city])
    return times[s:e], temps[s:e]


def forecast_noise_std(default: float = 0.13) -> float:
    """Standard deviation of the LightGBM 1-hour error from figures/metrics.json."""
    import json
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "figures" / "metrics.json"
    try:
        return float(json.loads(path.read_text())["h1"]["lightgbm_resid_std_c"])
    except (OSError, KeyError, ValueError):
        return default


if __name__ == "__main__":
    import sys

    if "--synthetic" in sys.argv:
        weather = synthetic_weather()
        for city, curve in CITIES.items():
            for name, s in savings_range(curve, weather).items():
                print(f"{city:6} {name:4}: saved {s.saved_kwh:6.1f} kWh ({s.saved_pct:4.1f} %)")
        print("SYNTHETIC WEATHER, not for the application")
        sys.exit()

    noise = forecast_noise_std()
    p = RoomParams()
    for city, curve in CITIES.items():
        times, temps = season_weather(city)
        print(f"\n{city}: season {times[0][:10]} .. {times[-1][:10]} ({len(temps) // 24} days), "
              f"mean {sum(temps) / len(temps):.1f} C, forecast noise std {noise:.3f} C")
        for name, s in savings_range(curve, temps, noise_std=noise).items():
            b, m = s.baseline, s.smart
            print(f"  {name:4}: without {b.energy_kwh:6.0f} kWh, SmartHeat {m.energy_kwh:6.0f} kWh, "
                  f"saved {s.saved_kwh:5.0f} kWh ({s.saved_pct:4.1f} %) | >24C {b.hours_above(24):5.0f} h -> "
                  f"{m.hours_above(24):3.0f} h | <20C {b.hours_below(20):4.0f} -> {m.hours_below(20):4.0f} h | "
                  f"window open {b.window_hours():5.0f} h")
        thermo = run_smart(p, curve, temps, thermostat_predictor())
        smart = run_smart(p, curve, temps, physics_predictor(p, curve, noise_std=noise))
        print(f"  thermostat without forecast: {thermo.energy_kwh:6.0f} kWh, >22.5C {thermo.hours_above(22.5):4.0f} h, "
              f"<20C {thermo.hours_below(20):3.0f} h | with forecast: {smart.energy_kwh:6.0f} kWh, "
              f">22.5C {smart.hours_above(22.5):4.0f} h, <20C {smart.hours_below(20):3.0f} h")
    print("\nBaku sensitivity to design temperature (assumption):")
    times, temps = season_weather("Baku")
    for d in (-7.0, -4.0, -1.0):
        s = compare(p, replace(CITIES["Baku"], t_out_design=d), temps, physics_predictor(p, replace(CITIES["Baku"], t_out_design=d), noise_std=noise))
        print(f"  design {d:5.1f} C: saved {s.saved_kwh:5.0f} kWh ({s.saved_pct:4.1f} %)")
