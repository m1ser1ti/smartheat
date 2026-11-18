"""Builds demo.json for the SmartHeat app.

The format is described in docs/demo_json.md. For now it only builds a stub on synthetic
weather (--stub): the file has "synthetic": true and the app shows a "Synthetic data"
banner. Open-Meteo weather and LightGBM are plugged in after steps 4-5.

Run: python3 src/export.py --stub
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import simulate as sim

ROOT = Path(__file__).resolve().parents[1]
APP_JSON = ROOT / "ios" / "SmartHeat" / "SmartHeat" / "demo.json"
SCHEMA_VERSION = 1
FORECAST_STEP_MIN = 15
FORECAST_HORIZON_MIN = 180
BUILDING_ROOMS = 100

# Tariffs and emission factors: fill in from sources (IR), None until then.
FACTORS = {
    "Astana": {"currency": "KZT", "tariff_per_kwh": None, "co2_kg_per_kwh": None},
    "Baku": {"currency": "AZN", "tariff_per_kwh": None, "co2_kg_per_kwh": None},
}

ADVICE = {
    "close_window": ("warning", "Close the window",
                     "The room is warm because the radiator runs at full power. "
                     "Opening the window wastes that heat; SmartHeat will turn the valve down instead."),
    "overheat_soon": ("warning", "Overheating expected",
                      "The forecast shows more than {threshold:.0f} °C in about {minutes} min. "
                      "The smart valve is closing to keep {target:.0f} °C."),
    "comfort_ok": ("info", "Comfort is fine",
                   "The room stays between {tmin:.0f} and {tmax:.0f} °C for the next 3 hours."),
    "night": ("info", "Night mode",
              "At night 20-21 °C is enough for good sleep and saves heat."),
    "ventilate_short": ("info", "Ventilate briefly",
                        "If you need fresh air, open the window wide for 5 minutes instead of keeping it ajar."),
    "cold_snap": ("info", "Cold weather ahead",
                  "It will get colder outside; the valve will open more to keep you warm."),
}


def _advice(key: str, **kw) -> dict:
    severity, title, text = ADVICE[key]
    return {"id": key, "severity": severity, "title": title, "text": text.format(**kw)}


def _pick_overheat_moment(baseline: sim.RunResult, threshold: float) -> int:
    """First hour that is still below the threshold now but goes above it within 3 h (window closed)."""
    horizon = FORECAST_HORIZON_MIN // FORECAST_STEP_MIN
    for i in range(0, len(baseline.temps) - horizon, sim.STEPS_PER_HOUR):
        if baseline.windows[i]:
            continue
        ahead = baseline.temps[i:i + horizon + 1]
        if ahead[0] < threshold - 1.0 and max(ahead) > threshold:
            return i
    return 0


def _rollout(p, curve, t0, t_out, horizon_steps, smart: bool, predictor=None):
    temps, valve = [t0], 1.0
    t = t0
    for _ in range(horizon_steps):
        if smart:
            valve = next((v for v in sim.VALVE_LEVELS if predictor(t, t_out, v) <= 22.0), 0.0)
        t, _ = sim.step(p, curve, t, t_out, valve, window=False)
        temps.append(t)
    return temps, valve


def build_stub(city: str = "Astana", days: int = 30) -> dict:
    p = sim.RoomParams()
    curve = sim.CITIES[city]
    weather = sim.synthetic_weather(days=days)
    expanded = [t for t in weather for _ in range(sim.STEPS_PER_HOUR)]
    threshold, tmin, tmax = 24.0, 21.0, 22.0

    baseline = sim.run_baseline(p, curve, weather)
    i = _pick_overheat_moment(baseline, threshold)
    t_now, t_out = baseline.temps[i], expanded[i]
    horizon = FORECAST_HORIZON_MIN // FORECAST_STEP_MIN
    predictor = sim.physics_predictor(p, curve)
    no_action, _ = _rollout(p, curve, t_now, t_out, horizon, smart=False)
    with_system, valve_now = _rollout(p, curve, t_now, t_out, horizon, smart=True, predictor=predictor)

    over = next((k * FORECAST_STEP_MIN for k, t in enumerate(no_action) if t > threshold), None)
    advice = []
    if over is not None:
        advice.append(_advice("overheat_soon", threshold=threshold, minutes=over, target=tmax))
    advice += [_advice("close_window"), _advice("ventilate_short"), _advice("night")]

    savings = []
    for c_name, c_curve in sim.CITIES.items():
        r = sim.savings_range(c_curve, weather)
        f = FACTORS[c_name]

        def scaled(factor):
            if factor is None:
                return None
            return {k: round(v.saved_kwh * factor, 1) for k, v in r.items()}

        savings.append({
            "city": c_name,
            "period_days": days,
            "scope": "room",
            "building_rooms": BUILDING_ROOMS,
            "kwh": {k: round(v.saved_kwh, 1) for k, v in r.items()},
            "percent": {k: round(v.saved_pct, 1) for k, v in r.items()},
            "money": None if f["tariff_per_kwh"] is None else {"currency": f["currency"], **scaled(f["tariff_per_kwh"])},
            "co2_kg": scaled(f["co2_kg_per_kwh"]),
            "hours_above_24": {"baseline": round(r["base"].baseline.hours_above(threshold), 1),
                               "smart": round(r["base"].smart.hours_above(threshold), 1)},
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "synthetic": True,
        "notes": ["Synthetic weather and physics forecast stub. Not for the application."],
        "room": {
            "name": "Living room",
            "city": city,
            "temp_now": round(t_now, 1),
            "temp_outside": round(t_out, 1),
            "target_min": tmin,
            "target_max": tmax,
            "overheat_threshold": threshold,
            "window_open": False,
            "valve": valve_now,
        },
        "forecast": {
            "model": "physics-stub",
            "step_minutes": FORECAST_STEP_MIN,
            "mae_hour1_c": None,
            "mae_hour3_c": None,
            "points": [{"minutes": k * FORECAST_STEP_MIN, "temp": round(a, 2), "temp_with_system": round(b, 2)}
                       for k, (a, b) in enumerate(zip(no_action, with_system))],
        },
        "alert": {
            "overheat_in_minutes": over,
            "title": "Overheating soon",
            "body": f"Room will pass {threshold:.0f} °C in {over} min. Close the window, SmartHeat turns the valve down."
            if over is not None else None,
        },
        "advice": advice,
        "savings": savings,
        "assumptions": sim.ASSUMPTIONS,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stub", action="store_true", help="stub on synthetic weather")
    ap.add_argument("--out", type=Path, default=APP_JSON)
    args = ap.parse_args()
    if not args.stub:
        ap.error("only --stub for now: real data arrives after steps 4-5")
    data = build_stub()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written {args.out.relative_to(ROOT)} (synthetic={data['synthetic']})")


if __name__ == "__main__":
    main()
