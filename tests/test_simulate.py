"""Tests for the RC room model. Run: python3 tests/test_simulate.py -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import simulate as sim  # noqa: E402


class HeatingCurveTest(unittest.TestCase):
    def test_design_point_and_clamps(self):
        c = sim.HeatingCurve(t_out_design=-31.0)
        self.assertAlmostEqual(c.supply(-31.0), 95.0)
        self.assertAlmostEqual(c.supply(-40.0), 95.0)   # upper cap
        self.assertAlmostEqual(c.supply(5.0), 60.0)     # lower break point
        self.assertTrue(60.0 < c.supply(-20.0) < 95.0)


class PhysicsTest(unittest.TestCase):
    def test_converges_to_analytic_equilibrium(self):
        p, c = sim.RoomParams(), sim.HeatingCurve(t_out_design=-31.0)
        t_out, valve = -10.0, 0.5
        t_rad = c.supply(t_out) - p.radiator_drop
        k = valve * p.k_radiator
        expected = (k * t_rad + p.internal_gains + p.ua_closed() * t_out) / (k + p.ua_closed())
        t = 21.0
        for _ in range(sim.STEPS_PER_HOUR * 24 * 20):
            t, _ = sim.step(p, c, t, t_out, valve, window=False)
        self.assertAlmostEqual(t, expected, places=2)

    def test_open_window_cools(self):
        p, c = sim.RoomParams(), sim.HeatingCurve(t_out_design=-31.0)
        closed, _ = sim.step(p, c, 22.0, -10.0, 1.0, window=False)
        opened, _ = sim.step(p, c, 22.0, -10.0, 1.0, window=True)
        self.assertLess(opened, closed)


class ScenarioTest(unittest.TestCase):
    def setUp(self):
        self.p = sim.RoomParams()
        self.curve = sim.CITIES["Astana"]

    def test_mild_weather_smart_saves_and_avoids_overheating(self):
        weather = [2.0] * 24 * 7  # mild weather: the curve break point causes overheating
        s = sim.compare(self.p, self.curve, weather)
        self.assertGreater(s.baseline.hours_above(24.0), 0)
        self.assertEqual(s.smart.hours_above(24.0), 0)
        self.assertGreater(s.saved_kwh, 0)

    def test_smart_keeps_comfort(self):
        weather = sim.synthetic_weather(days=14)
        smart = sim.run_smart(self.p, self.curve, weather)
        later = smart.temps[sim.STEPS_PER_HOUR * 24:]  # after the first day
        self.assertGreaterEqual(min(later), 20.0)
        self.assertLessEqual(max(later), 22.5)

    def test_design_cold_no_fake_savings(self):
        weather = [-31.0] * 24 * 7  # design frost: no overheating, nothing to save
        s = sim.compare(self.p, self.curve, weather)
        self.assertLess(abs(s.saved_pct), 2.0)

    def test_forecast_bias_changes_control(self):
        weather = [2.0] * 24 * 3
        cautious = sim.run_smart(self.p, self.curve, weather, sim.physics_predictor(self.p, self.curve, bias=+0.5))
        exact = sim.run_smart(self.p, self.curve, weather)
        self.assertLess(cautious.energy_kwh, exact.energy_kwh)

    def test_noisy_forecast_is_reproducible_and_keeps_comfort(self):
        weather = sim.synthetic_weather(days=10)
        runs = [sim.run_smart(self.p, self.curve, weather, sim.physics_predictor(self.p, self.curve, noise_std=0.13, seed=1))
                for _ in range(2)]
        self.assertEqual(runs[0].energy_kwh, runs[1].energy_kwh)
        later = runs[0].temps[sim.STEPS_PER_HOUR * 24:]
        self.assertGreaterEqual(min(later), 20.0)
        self.assertLessEqual(max(later), 22.8)

    def test_thermostat_predictor_ignores_valve(self):
        pred = sim.thermostat_predictor()
        self.assertEqual(pred(21.5, -10.0, 0.0), pred(21.5, -10.0, 1.0))

    def test_range_is_ordered(self):
        r = sim.savings_range(self.curve, sim.synthetic_weather(days=14))
        self.assertLessEqual(r["low"].saved_kwh, r["base"].saved_kwh)
        self.assertLessEqual(r["base"].saved_kwh, r["high"].saved_kwh)


class HeatingSeasonTest(unittest.TestCase):
    @staticmethod
    def _hours(daily_means):
        times, temps = [], []
        for d, m in enumerate(daily_means):
            day = f"2025-10-{d + 1:02d}" if d < 31 else f"2025-11-{d - 30:02d}"
            for h in range(24):
                times.append(f"{day}T{h:02d}:00")
                temps.append(m)
        return times, temps

    def test_starts_on_first_cold_five_days(self):
        means = [12, 12, 9, 9, 9, 9, 11] + [9] * 5 + [5] * 10  # first cold 5-day run starts on day 8
        times, temps = self._hours(means)
        start, end = sim.heating_season(times, temps, threshold=10.0)
        self.assertEqual(times[start], "2025-10-08T00:00")
        self.assertEqual(times[end - 1], times[-1])

    def test_no_season_raises(self):
        times, temps = self._hours([15] * 10)
        with self.assertRaises(ValueError):
            sim.heating_season(times, temps, threshold=10.0)


if __name__ == "__main__":
    unittest.main()
