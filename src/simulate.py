"""RC model of a room with district heating: two scenarios and the savings estimate.

Standard library only: runs without pandas or numpy.

Scenarios:
- baseline: the radiator valve is always open (typical riser without control),
  the occupant opens the window above 24 °C and closes it below 22 °C;
- smart: the window stays closed (the app's advice is followed) and the smart valve picks
  the largest opening for which the 1-hour temperature FORECAST stays at or below 22 °C.
  The forecast comes from a predictor function: for now a physics predictor
  (the same RC model); LightGBM replaces it after training.

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
    # Design temperatures are assumptions: check against SP RK 2.04-01 and Azerbaijani norms.
    "Astana": HeatingCurve(t_out_design=-31.0),
    "Baku": HeatingCurve(t_out_design=-4.0),
}

ASSUMPTIONS = [
    "Room ~20 m2 in a panel building, envelope UA 25 W/K, infiltration 9 W/K",
    "Open window adds 60 W/K (range 30-90)",
    "Supply curve 95 C at design outdoor temperature, 40 C at +8 C, minimum 60 C (range 55-65)",
    "Baseline: radiator valve always open, window opened above 24 C, closed below 22 C",
    "Smart: window kept closed, valve throttled when the 1-hour forecast exceeds 22 C",
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


def physics_predictor(p: RoomParams, curve: HeatingCurve, bias: float = 0.0) -> Predictor:
    """Forecast with the same RC model; bias imitates the error of the future ML model."""

    def predict(t_in: float, t_out: float, valve: float) -> float:
        t = t_in
        for _ in range(STEPS_PER_HOUR):
            t, _ = step(p, curve, t, t_out, valve, window=False)
        return t + bias

    return predict


@dataclass
class RunResult:
    energy_kwh: float
    temps: list[float]
    valves: list[float]
    windows: list[bool]

    def hours_above(self, threshold: float) -> float:
        return sum(1 for t in self.temps if t > threshold) / STEPS_PER_HOUR

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
                  base: RoomParams = RoomParams()) -> dict[str, Savings]:
    """Savings under cautious, base and bold assumptions (the range quoted in the application)."""
    variants = {
        "low": (replace(base, ua_window_open=30.0), replace(curve, t_supply_min=55.0)),
        "base": (base, curve),
        "high": (replace(base, ua_window_open=90.0), replace(curve, t_supply_min=65.0)),
    }
    return {name: compare(p, c, weather_hourly) for name, (p, c) in variants.items()}


def synthetic_weather(days: int = 30, start: float = -20.0, end: float = 5.0, daily_amp: float = 4.0) -> list[float]:
    """Synthetic weather for tests and the stub: linear trend + daily cycle. NOT for the application."""
    import math

    n = days * 24
    return [start + (end - start) * i / max(1, n - 1) + daily_amp * math.sin(2 * math.pi * (i % 24 - 9) / 24)
            for i in range(n)]


if __name__ == "__main__":
    weather = synthetic_weather()
    for city, curve in CITIES.items():
        for name, s in savings_range(curve, weather).items():
            print(f"{city:6} {name:4}: baseline {s.baseline.energy_kwh:7.1f} kWh, smart {s.smart.energy_kwh:7.1f} kWh, "
                  f"saved {s.saved_kwh:6.1f} kWh ({s.saved_pct:4.1f} %), "
                  f">24C baseline {s.baseline.hours_above(24):5.1f} h, smart {s.smart.hours_above(24):4.1f} h")
    print("SYNTHETIC WEATHER, not for the application")
