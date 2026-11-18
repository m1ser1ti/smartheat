# SmartHeat

Our project for the **CECECO Clean Energy Hackathon 2027** (track "Bring Clean Energy to Everyday Life").

## The problem

In many buildings in Kazakhstan and Azerbaijan, heat comes from a central system. Nobody can turn it down
in their own room. In spring and autumn rooms get too hot, so people open the windows, and the heat goes outside.

## Our idea

1. A small sensor measures the room temperature.
2. A computer model predicts how warm the room will be in the next 1-3 hours.
3. If the room is about to get too hot, a smart valve turns the radiator down before it happens.
4. An iPhone app shows the room, the forecast, tips and how much energy is saved.

The sensors and valves are only a concept for now. The model, the simulation and the app work.

## What we got

- The forecast is off by only about **0.1-0.2 °C** (tested on real data from two houses).
- In a simulated room in Astana, the system saves about **6-19 % of the heat** over one winter
  and stops the room from overheating.

All numbers come with their sources and assumptions in [SOURCES.md](SOURCES.md).

## What is in this folder

| Folder | What it is |
|---|---|
| `src/` | Python code: weather, data cleaning, model, simulation, app data, charts |
| `ios/SmartHeat/` | The iPhone app |
| `figures/` | Charts and results for the application |
| `tests/` | Checks for the simulation |
| `docs/` | Format of the app data file |


## How to run

```bash
python3 -m venv .venv && .venv/bin/pip install --only-binary :all: -r requirements.txt
```

```bash
.venv/bin/python src/weather.py && .venv/bin/python src/prepare.py && .venv/bin/python src/model.py && .venv/bin/python src/export.py && .venv/bin/python src/figures.py
```

The dataset has to be downloaded first (link in [SOURCES.md](SOURCES.md)). On a Mac, LightGBM also needs `brew install libomp`.

To see the app, open `ios/SmartHeat/SmartHeat.xcodeproj` in Xcode and press Run.

## Team

Four students from ADA University, Baku.
