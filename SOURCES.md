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

- What we used: `ThermBuild_measure_imputed.zip` (downloaded 18.11.2026), both houses, 14 rooms, heating months.
- The year 2025 is inferred from `day_of_the_year` (start 38 = 7 February, year rolls over after day 365) and from the paper (validation in March 2025).
- Windows were never opened in the real measurements (`win` = 0): the model did not learn the window effect from this data.

### Open-Meteo (weather)
- Historical Weather API, https://open-meteo.com/en/docs/historical-weather-api, downloaded 18.11.2026
- Terms: https://open-meteo.com/en/terms. The free API is for non-commercial use only, data under CC BY 4.0 (attribution to Open-Meteo required).
- Astana (51.17, 71.45) and Baku (40.41, 49.87), hourly temperature 01.09.2025-31.05.2026.

## Simulation numbers and assumptions

| What | Value | Source | Status |
|---|---|---|---|
| Astana design temperature (coldest five-day period) | -31.2 °C | design documentation on ecoportal.kz (e.g. https://ecoportal.kz/Disscusion/DisHearings/LoadFile/112386); standard SP RK 2.04-01-2017 | check against the SP RK table |
| Heating start in Astana | daily mean ≤ +10 °C for 5 days | https://kazpravda.kz/n/stalo-izvestno-kogda-dadut-otoplenie-v-stolitse/ | ok |
| Baku design temperature | -4 °C | not found | assumption, sensitivity 45-51 % savings at -7..-1 °C |
| Heating start in Baku | ≤ +8 °C for 5 days | SNiP rule, not confirmed for Baku | assumption |
| Curve break point (network supply not below ~70 °C), cause of shoulder-season overheating | 60 °C at the radiator in the model (55-65) | https://habr.com/en/articles/808175 ; ABOK https://www.abok.ru/for_spec/articles/43/8698/8698.pdf ; TPU https://portal.tpu.ru/SHARED/l/LBA/learning/system/Tab2/L9_p.pdf | the radiator value is an assumption |
| CO2 of coal (other bituminous) | 94.6 t CO2/TJ = 0.341 kg/kWh of fuel | IPCC 2006 GL, Vol. 2, Ch. 1, Table 1.4; repeated in EU 2018/2066 Annex VI https://www.legislation.gov.uk/eur/2018/2066/annex/VI/data.pdf | ok |
| CO2 of natural gas | 56.1 t CO2/TJ = 0.202 kg/kWh of fuel | same | ok |
| Heat generation efficiency | 0.85 (coal, Astana), 0.90 (gas, Baku) | assumption | ask IR |
| Heat tariffs KZ/AZ | none | from IR | expected by 23 November |

## Results (citable in the application)
- Model: `figures/metrics.json`. Test 01.02-25.04.2026, 14 rooms, 28,210 room-hours. LightGBM MAE 0.079 °C (1 h) and 0.168 °C (3 h) vs 0.126 and 0.313 °C for the no-change forecast.
- Savings: `figures/savings_summary.json`. Astana 5.6-18.8 % of heat (base 11.5 %, 484 kWh per room over the 2025/26 season). Baku 39-54 %, strongly assumption-dependent.
- A plain thermostat without a forecast saves almost as much in the simulation (3728 vs 3721 kWh in Astana): the automatic valve delivers the savings, the forecast adds lead time and alerts.
