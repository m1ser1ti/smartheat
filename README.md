# SmartHeat CA

Room temperature forecast 1-3 hours ahead and a smart radiator valve against overheating in buildings
with district heating (Kazakhstan, Azerbaijan). CECECO Clean Energy Hackathon 2027.

Demo: an iPhone app driven by `demo.json`. Hardware (sensors, valves) is at the concept stage.
Sources and licenses: [SOURCES.md](SOURCES.md).

## What is where

| Path | What it does |
|---|---|
| `src/simulate.py` | RC room model, "without system" and "with system" scenarios, savings range |
| `src/export.py` | builds `demo.json` for the app |
| `docs/demo_json.md` | `demo.json` format |
| `tests/` | simulation tests |
| `ios/SmartHeat/` | SwiftUI app: Room, Forecast, Savings screens, local notification |
| `data/` | datasets (not in git) |

## How to run

Simulation and tests (Python standard library only):

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

## Status

- The simulation runs on synthetic weather; the numbers are not for the application.
- The LightGBM model is not trained yet: the forecast in `demo.json` is physics-based (`physics-stub`).
- Tariffs and CO2 factors are not set: money and CO2 show as "awaiting" in the app.
