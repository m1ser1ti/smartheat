"""Builds demo.json for the SmartHeat app (format: docs/demo_json.md).

Default mode: the room is simulated with the RC model on last winter's real Open-Meteo weather;
forecast error and MAE come from LightGBM on ThermBuild test data (figures/metrics.json).
--stub: synthetic weather; the file has "synthetic": true and the app shows a banner.

Run: python3 src/export.py           (needs data/raw/weather_*.csv and figures/metrics.json)
     python3 src/export.py --stub
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import simulate as sim

ROOT = Path(__file__).resolve().parents[1]
APP_JSON = ROOT / "ios" / "SmartHeat" / "SmartHeat" / "demo.json"
METRICS = ROOT / "figures" / "metrics.json"
SUMMARY = ROOT / "figures" / "savings_summary.json"
SCHEMA_VERSION = 1
FORECAST_STEP_MIN = 15
FORECAST_HORIZON_MIN = 180
BUILDING_ROOMS = 100
OVERHEAT, ALERT_AT, T_MIN, T_MAX = 24.0, 23.5, 21.0, 22.0
DEMO_CITY = "Astana"

# CO2 per kWh of heat = IPCC 2006 fuel factor / generation efficiency (assumption). Network losses excluded.
# Tariffs: from IR (due 23 November), None until then.
KWH_PER_TJ = 277_777.8
FACTORS = {
    "Astana": {"currency": "KZT", "tariff_per_kwh": None,
               "fuel": "coal (IPCC other bituminous, 94.6 t CO2/TJ)", "co2_kg_per_kwh": 94_600 / KWH_PER_TJ / 0.85},
    "Baku": {"currency": "AZN", "tariff_per_kwh": None,
             "fuel": "natural gas (IPCC, 56.1 t CO2/TJ)", "co2_kg_per_kwh": 56_100 / KWH_PER_TJ / 0.90},
}

ADVICE = {
    "overheat_soon": ("warning", "Overheating expected",
                      "Without action the room passes {threshold:.0f} °C in about {minutes} min. "
                      "SmartHeat is turning the radiator valve down to keep {target:.0f} °C."),
    "close_window": ("warning", "Keep the window closed",
                     "Opening the window to cool an overheated room throws the heat outside. "
                     "Let the valve reduce the heating instead."),
    "ventilate_short": ("info", "Ventilate briefly",
                        "For fresh air, open the window wide for 5 minutes instead of keeping it ajar for hours."),
    "night": ("info", "Night mode",
              "At night 20-21 °C is enough for good sleep and saves heat."),
    "cold_snap": ("info", "Cold weather ahead",
                  "It will get colder outside; the valve will open more to keep you warm."),
}


def _advice(key: str, **kw) -> dict:
    severity, title, text = ADVICE[key]
    return {"id": key, "severity": severity, "title": title, "text": text.format(**kw)}


def _rollout(p, curve, t0, t_out_steps, smart: bool, predictor=None):
    temps, valve, t = [t0], 1.0, t0
    first_valve = None
    for t_out in t_out_steps:
        if smart:
            valve = next((v for v in sim.VALVE_LEVELS if predictor(t, t_out, v) <= T_MAX), 0.0)
        first_valve = valve if first_valve is None else first_valve
        t, _ = sim.step(p, curve, t, t_out, valve, window=False)
        temps.append(t)
    return temps, first_valve


def _pick_moment(baseline: sim.RunResult, temps_15: list[float]) -> int:
    """A typical shoulder-season moment for the demo: window closed, -5..+5 °C outside, below 23.5 °C now,
    and without action the room passes 24 °C in 45-120 min. Falls back to a looser rule if none is found."""
    horizon = FORECAST_HORIZON_MIN // FORECAST_STEP_MIN
    rules = [(-5.0, 5.0, 45, 120, 23.5), (-15.0, 12.0, 15, FORECAST_HORIZON_MIN, 23.0)]
    for t_lo, t_hi, m_lo, m_hi, t_now_max in rules:
        for i in range(0, len(baseline.temps) - horizon, sim.STEPS_PER_HOUR):
            if baseline.windows[i] or baseline.temps[i] >= t_now_max or not t_lo <= temps_15[i] <= t_hi:
                continue
            ahead = baseline.temps[i:i + horizon + 1]
            cross = next((k * FORECAST_STEP_MIN for k, t in enumerate(ahead) if t > OVERHEAT), None)
            if cross is not None and m_lo <= cross <= m_hi:
                return i
    return 0


def _room_and_forecast(times: list[str], weather: list[float], curve, noise: float, metrics: dict | None):
    p = sim.RoomParams()
    baseline = sim.run_baseline(p, curve, weather)
    temps_15 = [t for t in weather for _ in range(sim.STEPS_PER_HOUR)]
    i = _pick_moment(baseline, temps_15)
    horizon = FORECAST_HORIZON_MIN // FORECAST_STEP_MIN
    t_now, t_out_steps = baseline.temps[i], temps_15[i:i + horizon]
    no_action, _ = _rollout(p, curve, t_now, t_out_steps, smart=False)
    with_system, valve_now = _rollout(p, curve, t_now, t_out_steps, smart=True,
                                      predictor=sim.physics_predictor(p, curve))
    over = next((k * FORECAST_STEP_MIN for k, t in enumerate(no_action) if t > OVERHEAT), None)
    moment = times[i // sim.STEPS_PER_HOUR]
    return {
        "name": "Living room", "city": DEMO_CITY,
        "temp_now": round(t_now, 1), "temp_outside": round(temps_15[i], 1),
        "target_min": T_MIN, "target_max": T_MAX, "overheat_threshold": OVERHEAT,
        "window_open": False, "valve": valve_now,
    }, {
        "model": f"Simulated room, real {DEMO_CITY} weather ({moment[:10]})",
        "step_minutes": FORECAST_STEP_MIN,
        "mae_hour1_c": metrics["h1"]["mae_c"]["lightgbm"] if metrics else None,
        "mae_hour3_c": metrics["h3"]["mae_c"]["lightgbm"] if metrics else None,
        "points": [{"minutes": k * FORECAST_STEP_MIN, "temp": round(a, 2), "temp_with_system": round(b, 2)}
                   for k, (a, b) in enumerate(zip(no_action, with_system))],
    }, over, moment


def _savings_entry(city: str, days: int, r: dict[str, sim.Savings]) -> dict:
    f = FACTORS[city]

    def scaled(factor):
        return None if factor is None else {k: round(v.saved_kwh * factor, 1) for k, v in r.items()}

    return {
        "city": city, "period_days": days, "scope": "room", "building_rooms": BUILDING_ROOMS,
        "kwh": {k: round(v.saved_kwh, 1) for k, v in r.items()},
        "percent": {k: round(v.saved_pct, 1) for k, v in r.items()},
        "money": None if f["tariff_per_kwh"] is None else {"currency": f["currency"], **scaled(f["tariff_per_kwh"])},
        "co2_kg": scaled(f["co2_kg_per_kwh"]),
        "hours_above_24": {"baseline": round(r["base"].baseline.hours_above(OVERHEAT), 1),
                           "smart": round(r["base"].smart.hours_above(OVERHEAT), 1)},
    }


def _assemble(room, forecast, over, advice, savings, synthetic: bool, notes: list[str]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "synthetic": synthetic,
        "notes": notes,
        "room": room,
        "forecast": forecast,
        "alert": {
            "overheat_in_minutes": over,
            "title": "Overheating soon",
            "body": (f"The room will pass {OVERHEAT:.0f} °C in {over} min. "
                     f"Keep the window closed: SmartHeat turns the radiator down.") if over is not None else None,
        },
        "advice": advice,
        "savings": savings,
        "assumptions": sim.ASSUMPTIONS + [
            f"CO2: {FACTORS[c]['fuel']}, generation efficiency {0.85 if c == 'Astana' else 0.90:.2f}, network losses excluded"
            for c in FACTORS],
    }


def _advice_list(over) -> list[dict]:
    advice = [_advice("overheat_soon", threshold=OVERHEAT, minutes=over, target=T_MAX)] if over is not None else []
    return advice + [_advice("close_window"), _advice("ventilate_short"), _advice("night")]


def build_real() -> tuple[dict, dict]:
    metrics = json.loads(METRICS.read_text())
    noise = metrics["h1"]["lightgbm_resid_std_c"]
    savings, summary = [], {"forecast_noise_std_c": noise, "cities": {}}
    room = forecast = over = None
    for city, curve in sim.CITIES.items():
        times, weather = sim.season_weather(city)
        r = sim.savings_range(curve, weather, noise_std=noise)
        savings.append(_savings_entry(city, len(weather) // 24, r))
        p = sim.RoomParams()
        thermo = sim.run_smart(p, curve, weather, sim.thermostat_predictor())
        summary["cities"][city] = {
            "season": [times[0][:10], times[-1][:10]], "days": len(weather) // 24,
            "mean_t_out_c": round(sum(weather) / len(weather), 2),
            **{name: {"without_kwh": round(s.baseline.energy_kwh, 1), "smartheat_kwh": round(s.smart.energy_kwh, 1),
                      "saved_kwh": round(s.saved_kwh, 1), "saved_pct": round(s.saved_pct, 1),
                      "hours_above_24_without": round(s.baseline.hours_above(OVERHEAT), 1),
                      "hours_above_24_smartheat": round(s.smart.hours_above(OVERHEAT), 1),
                      "hours_below_20_smartheat": round(s.smart.hours_below(20.0), 1),
                      "window_open_hours_without": round(s.baseline.window_hours(), 1)}
               for name, s in r.items()},
            "thermostat_no_forecast_kwh": round(thermo.energy_kwh, 1),
            "thermostat_hours_above_22_5": round(thermo.hours_above(22.5), 1),
            "co2_kg_per_kwh_heat": round(FACTORS[city]["co2_kg_per_kwh"], 4),
        }
        if city == DEMO_CITY:
            room, forecast, over, moment = _room_and_forecast(times, weather, curve, noise, metrics)
            summary["demo_moment"] = moment
    notes = [f"Room is simulated (RC model) on real {DEMO_CITY} weather from Open-Meteo; "
             "forecast error from LightGBM on ThermBuild test data."]
    return _assemble(room, forecast, over, _advice_list(over), savings, False, notes), summary


def build_stub(days: int = 30) -> dict:
    weather = sim.synthetic_weather(days=days)
    times = [f"synthetic-{i}" for i in range(len(weather))]
    room, forecast, over, _ = _room_and_forecast(times, weather, sim.CITIES[DEMO_CITY], 0.0, None)
    forecast["model"] = "physics-stub"
    savings = [_savings_entry(c, days, sim.savings_range(curve, weather)) for c, curve in sim.CITIES.items()]
    return _assemble(room, forecast, over, _advice_list(over), savings, True,
                     ["Synthetic weather and physics forecast stub. Not for the application."])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stub", action="store_true", help="stub on synthetic weather")
    ap.add_argument("--out", type=Path, default=APP_JSON)
    args = ap.parse_args()
    if args.stub:
        data = build_stub()
    else:
        data, summary = build_real()
        SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
        print(f"written {SUMMARY.relative_to(ROOT)}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shown = args.out.resolve()
    shown = shown.relative_to(ROOT) if shown.is_relative_to(ROOT) else shown
    print(f"written {shown} (synthetic={data['synthetic']})")


if __name__ == "__main__":
    main()
