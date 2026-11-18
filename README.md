# SmartHeat CA

Room temperature forecast 1-3 hours ahead and a smart radiator valve against overheating in buildings
with district heating (Kazakhstan, Azerbaijan). CECECO Clean Energy Hackathon 2027.

Demo: an iPhone app driven by `demo.json`. Hardware (sensors, valves) is at the concept stage.
Sources and licenses: [SOURCES.md](SOURCES.md).

## What is where

| Path | What it does |
|---|---|
| `src/weather.py` | Open-Meteo weather for Astana and Baku |
| `src/prepare.py` | cleans ThermBuild into an hourly table |
| `src/model.py` | LightGBM 1 and 3 hours ahead against baselines, metrics |
| `src/simulate.py` | RC room model, "without system" and "with system" scenarios, savings range |
| `src/export.py` | builds `demo.json` for the app |
| `src/figures.py` | charts for the application in `figures/` |
| `docs/demo_json.md` | `demo.json` format |
| `tests/` | simulation tests |
| `ios/SmartHeat/` | SwiftUI app: Room, Forecast, Savings screens, local notification |
| `data/` | datasets (not in git) |

## How to run

Environment (once; LightGBM on macOS needs OpenMP):

```bash
brew install libomp
```

```bash
python3 -m venv .venv && .venv/bin/pip install --only-binary :all: -r requirements.txt
```

Full pipeline in order: weather, cleaning, model, demo.json, charts. Download ThermBuild manually into `data/raw/thermbuild/` (link in SOURCES.md):

```bash
.venv/bin/python src/weather.py && .venv/bin/python src/prepare.py && .venv/bin/python src/model.py && .venv/bin/python src/export.py && .venv/bin/python src/figures.py
```

Savings simulation and tests only (Python standard library):

```bash
python3 src/simulate.py
```

```bash
python3 tests/test_simulate.py -v
```

`demo.json` stub on synthetic weather (the app shows a "Synthetic data" banner):

```bash
python3 src/export.py --stub
```

Build the app (needs Xcode 27; running it also needs the iOS simulator runtime: `xcodebuild -downloadPlatform iOS`):

```bash
cd ios/SmartHeat && xcodebuild -project SmartHeat.xcodeproj -scheme SmartHeat -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath build CODE_SIGNING_ALLOWED=NO build
```

Or open `ios/SmartHeat/SmartHeat.xcodeproj` in Xcode and press Run.

## Results

- Forecast (LightGBM, real ThermBuild measurements, test February-April 2026): MAE 0.079 °C at 1 hour and 0.168 °C at 3 hours,
  37 % and 46 % better than the no-change forecast. `figures/metrics.json`.
- Savings (RC room model, real weather of the 2025/26 season): Astana 5.6-18.8 % of heat, base 11.5 %.
  Baku 39-54 %, resting on assumptions. `figures/savings_summary.json`.
- Charts for the application: `figures/*.png`.
- Money is not computed yet: waiting for tariffs from IR.
