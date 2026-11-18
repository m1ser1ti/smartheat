"""Room temperature forecast 1 and 3 hours ahead: LightGBM against simple baselines.

Data: data/clean/rooms_hourly.csv (src/prepare.py), 2 ThermBuild houses, 14 rooms.
Time-based split (no leakage from the future):
  train  2025-02-07 .. 2025-12-31
  valid  2026-01-01 .. 2026-01-31  (early stopping)
  test   2026-02-01 .. 2026-04-25  (every number in the application comes from here)
Target: temperature change dT = T(t+h) - T(t). Metric: MAE in °C.
Weather at t+h is the observed one: it stands in for a weather forecast
(the real system would use the Open-Meteo forecast).

Output: figures/metrics.json, data/clean/test_predictions.csv, models/lgb_h{1,3}.txt
Run: .venv/bin/python src/model.py
"""
from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from prepare import load_clean

ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "figures" / "metrics.json"
PREDICTIONS = ROOT / "data" / "clean" / "test_predictions.csv"
MODELS = ROOT / "models"

HORIZONS = (1, 3)
TRAIN_END, VALID_END = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-01")
OVERHEAT = 24.0
SEED = 42


def make_features(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    out = []
    for (house, room), g in df.groupby(["house", "room"], sort=True):
        g = g.set_index("time").sort_index()
        g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))  # true time lags across gaps
        f = pd.DataFrame(index=g.index)
        f["house"], f["room"] = house, room
        t = g["t_air"]
        f["t_air"] = t
        for lag in (1, 2, 3, 6, 12, 24):
            f[f"t_air_lag{lag}"] = t.shift(lag)
        f["dT_1h"] = t - t.shift(1)
        f["dT_3h"] = t - t.shift(3)
        f["valve"] = g["valve"]
        f["valve_lag1"] = g["valve"].shift(1)
        f["valve_mean3"] = g["valve"].rolling(3, min_periods=1).mean()
        f["valve_mean12"] = g["valve"].rolling(12, min_periods=1).mean()
        f["t_out"] = g["t_out"]
        f["t_out_mean24"] = g["t_out"].rolling(24, min_periods=1).mean()
        f["t_out_future"] = g["t_out"].shift(-horizon)
        f["solar"] = g["solar"]
        f["solar_future"] = g["solar"].shift(-horizon)
        f["t_supply"] = g["t_supply"]
        f["heat_on"] = g["heat_on"]
        f["t_in_minus_out"] = t - g["t_out"]
        f["hour"] = f.index.hour
        f["dow"] = f.index.day_of_week
        f["target_dT"] = t.shift(-horizon) - t
        out.append(f)
    feats = pd.concat(out).rename_axis("time").reset_index()
    feats = feats.dropna(subset=["t_air", "target_dT"])
    feats["room_id"] = (feats["house"] + "_" + feats["room"]).astype("category")
    return feats


FEATURES = [
    "t_air", "t_air_lag1", "t_air_lag2", "t_air_lag3", "t_air_lag6", "t_air_lag12", "t_air_lag24",
    "dT_1h", "dT_3h", "valve", "valve_lag1", "valve_mean3", "valve_mean12",
    "t_out", "t_out_mean24", "t_out_future", "solar", "solar_future", "t_supply", "heat_on",
    "t_in_minus_out", "hour", "dow", "room_id",
]
NUMERIC = [f for f in FEATURES if f != "room_id"]


def split(feats: pd.DataFrame):
    train = feats[feats.time < TRAIN_END]
    valid = feats[(feats.time >= TRAIN_END) & (feats.time < VALID_END)]
    test = feats[feats.time >= VALID_END]
    return train, valid, test


def mae(a, b) -> float:
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


ALERT_THRESHOLDS = (24.0, 23.5, 23.0)


def overheat_scores(actual: np.ndarray, pred: np.ndarray, alert_at: float = OVERHEAT) -> dict:
    """Event: actual > 24 °C. Alert: forecast > alert_at (a lower threshold alerts earlier and more often)."""
    y, p = actual > OVERHEAT, pred > alert_at
    tp = int((y & p).sum())
    return {"alert_at_c": alert_at, "events": int(y.sum()), "alerts": int(p.sum()),
            "precision": round(float(tp / p.sum()), 3) if p.sum() else None,
            "recall": round(float(tp / y.sum()), 3) if y.sum() else None}


def run_horizon(df: pd.DataFrame, h: int) -> tuple[dict, pd.DataFrame]:
    feats = make_features(df, h)
    train, valid, test = split(feats)

    model = lgb.LGBMRegressor(n_estimators=3000, learning_rate=0.03, num_leaves=31, min_child_samples=50,
                              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                              random_state=SEED, verbose=-1)
    model.fit(train[FEATURES], train["target_dT"], eval_X=(valid[FEATURES],), eval_y=(valid["target_dT"],),
              eval_metric="l1", callbacks=[lgb.early_stopping(100, verbose=False)])

    ridge = make_pipeline(SimpleImputer(), StandardScaler(), Ridge(alpha=1.0))
    ridge.fit(train[NUMERIC], train["target_dT"])

    actual = (test["t_air"] + test["target_dT"]).to_numpy()
    preds = {
        "persistence": test["t_air"].to_numpy(),
        "ridge": (test["t_air"] + ridge.predict(test[NUMERIC])).to_numpy(),
        "lightgbm": (test["t_air"] + model.predict(test[FEATURES], num_iteration=model.best_iteration_)).to_numpy(),
    }
    resid = actual - preds["lightgbm"]
    per_room = (pd.DataFrame({"room": test["room_id"].astype(str).to_numpy(),
                              "lgb": np.abs(resid), "persist": np.abs(actual - preds["persistence"])})
                .groupby("room").mean().round(3))
    gain = pd.Series(model.booster_.feature_importance("gain"), index=FEATURES)
    metrics = {
        "horizon_h": h,
        "n_train": len(train), "n_valid": len(valid), "n_test": len(test),
        "best_iteration": int(model.best_iteration_),
        "mae_c": {k: round(mae(actual, v), 4) for k, v in preds.items()},
        "lightgbm_resid_std_c": round(float(np.std(resid)), 4),
        "lightgbm_resid_p95_abs_c": round(float(np.quantile(np.abs(resid), 0.95)), 4),
        "skill_vs_persistence": round(1 - mae(actual, preds["lightgbm"]) / mae(actual, preds["persistence"]), 3),
        "overheat_24c": {k: [overheat_scores(actual, v, a) for a in ALERT_THRESHOLDS] for k, v in preds.items()},
        "per_room_mae_c": per_room.to_dict(orient="index"),
        "feature_gain_share": (gain / gain.sum()).sort_values(ascending=False).round(4).to_dict(),
    }
    MODELS.mkdir(exist_ok=True)
    model.booster_.save_model(str(MODELS / f"lgb_h{h}.txt"), num_iteration=model.best_iteration_)

    out = pd.DataFrame({"time": test["time"].to_numpy(), "house": test["house"].to_numpy(),
                        "room": test["room"].to_numpy(), "horizon": h, "actual": actual, **preds})
    return metrics, out


def main() -> None:
    df = load_clean()
    results, preds = {}, []
    for h in HORIZONS:
        m, p = run_horizon(df, h)
        results[f"h{h}"] = m
        preds.append(p)
        print(f"h={h}: MAE persistence {m['mae_c']['persistence']:.3f}, ridge {m['mae_c']['ridge']:.3f}, "
              f"LightGBM {m['mae_c']['lightgbm']:.3f} °C (skill {m['skill_vs_persistence']:.0%}), "
              f"n_test {m['n_test']}, iters {m['best_iteration']}")
        for name, rows in m["overheat_24c"].items():
            print(f"     {name:11} overheat>24 " + " | ".join(
                f"alert>{r['alert_at_c']}: P {r['precision']} R {r['recall']} ({r['alerts']})" for r in rows))
        print("     top features:", list(m["feature_gain_share"].items())[:6])
    results["split"] = {"train_end": str(TRAIN_END.date()), "valid_end": str(VALID_END.date()),
                        "test": "2026-02-01..2026-04-25"}
    results["data"] = "ThermBuild measured (2 TwinHouses, 14 rooms), heating months, hourly"
    METRICS.parent.mkdir(exist_ok=True)
    METRICS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n")
    pd.concat(preds).to_csv(PREDICTIONS, index=False, float_format="%.4f")
    print(f"-> {METRICS.relative_to(ROOT)}, {PREDICTIONS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
