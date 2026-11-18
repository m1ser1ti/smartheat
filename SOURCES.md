# Data and number sources

Every dataset and every number in the application must be listed here: name, link, license, what exactly we used.

## Datasets

### ThermBuild (main)
- Name: ThermBuild: Real-world and simulated thermal data from 960 residential multi-zone buildings
- Paper: arXiv:2606.01994 (v2, 3 June 2026), https://arxiv.org/abs/2606.01994
- Data: Fordatis (Fraunhofer), https://fordatis.fraunhofer.de/handle/fordatis/486, DOI 10.24406/fordatis/445
- License: CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Attribution required; derived datasets must be shared under the same license.
- Contents: 2 real houses (TwinHouses) + 958 TRNSYS simulations, Central Europe, 15-minute step.
  Per-room columns: `roomID_Tair` (°C), `roomID_Tset` (°C), `roomID_valve` (0-1), `roomID_win` (0-1), `roomID_rh` (%), `roomID_Tret` (°C); weather.
- Files: `ThermBuild_measure_imputed.zip` 15.8 MB (real measurements, gaps filled), `ThermBuild_measure_raw.zip` 15.1 MB, `ThermBuild_Sim.zip` 13.1 GB (simulations).
- Caveats for the application:
  - Private houses with underfloor heating from a heat pump, not radiators on district heating. The model learns room physics (window, valve, weather -> temperature); transferring it to KZ/AZ buildings is an assumption.
  - Central European climate, while the savings simulation runs on Astana and Baku weather.
  - Setpoint in the real houses is 20 °C with no night setback.

### Open-Meteo (weather)
- Historical Weather API, https://open-meteo.com/en/docs/historical-weather-api
- Data license: CC BY 4.0 (check https://open-meteo.com/en/license before submitting)
- Cities: Astana, Baku; last winter.

## Numbers (tariffs, CO2, cost estimate prices)
_Filled in as we go: value, source, date accessed._
