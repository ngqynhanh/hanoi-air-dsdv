# API / source notes and variable list

Week 1 deliverable. Everything below was confirmed against live API responses
(see `data/raw/collection_metadata.json`); settings live in `scripts/config.py`.

## 1. Sources

| | Air quality | Historical weather |
|---|---|---|
| API | Open-Meteo Air Quality API | Open-Meteo Historical Weather API |
| Endpoint | `https://air-quality-api.open-meteo.com/v1/air-quality` | `https://archive-api.open-meteo.com/v1/archive` |
| Underlying data | CAMS global atmospheric composition model (Copernicus) | Reanalysis, "best match" of ECMWF models (ERA5 family / IFS) |
| Nature of values | **Modelled**, not station measurements | **Modelled** (reanalysis), not station measurements |
| Time step | Hourly | Hourly |
| API key | Not required (free, non-commercial use, rate limited) | Not required |
| Docs | https://open-meteo.com/en/docs/air-quality-api | https://open-meteo.com/en/docs/historical-weather-api |

Licence/attribution: Open-Meteo data is CC BY 4.0; CAMS and ERA5 require crediting
Copernicus. The report and the AirLens footer should cite both.

## 2. Request parameters used

| Parameter | Value | Note |
|---|---|---|
| `latitude`, `longitude` | city-centre coordinates (table below) | API snaps to the nearest model grid cell |
| `start_date`, `end_date` | `2022-12-31` to `2026-10-31` | requested per calendar year to keep calls small |
| `hourly` | comma-separated variable list (section 4) | |
| `timezone` | `GMT` | raw files stay in UTC; conversion to UTC+7 is done in cleaning |

Other endpoints/parameters available but not used yet: `current=` (current conditions) and
`forecast_days=` on the air-quality endpoint (optional "short forecast view" feature);
`past_days=`; `domains=cams_global`.

Rate limit: the free tier counts weighted calls (long periods / many variables weigh more).
The collector waits 3 s between calls and retries with back-off on HTTP 429.

## 3. Cities and coordinates

| City | Requested lat, lon | Air-quality grid cell | Weather grid cell |
|---|---|---|---|
| Hanoi | 21.0285, 105.8542 | 21.0, 105.9 | 21.0545, 105.8985 |
| Ho Chi Minh City | 10.8231, 106.6297 | 10.8, 106.6 | 10.7909, 106.6313 |
| Da Nang | 16.0544, 108.2022 | 16.1, 108.2 | 16.0633, 108.2386 |
| Hai Phong | 20.8449, 106.6881 | 20.8, 106.7 | 20.8436, 106.6700 |

Each city is represented by one model grid cell, so values describe the regional
background, not a street or a single district. This matters for the optional
"map of Hanoi with 8-12 districts": neighbouring district coordinates may fall into the
same or adjacent cells and return near-identical series (the older
`hanoi_air_quality_openmeteo.csv` should be checked for this before building that map).

## 4. Variable list

### Air quality (10 variables)

| API name | Meaning | Unit | Availability in our period |
|---|---|---|---|
| `pm2_5` | Particulate matter < 2.5 µm | µg/m³ | complete |
| `pm10` | Particulate matter < 10 µm | µg/m³ | complete |
| `carbon_monoxide` | CO | µg/m³ | complete |
| `carbon_dioxide` | CO2 | ppm | **only from 2024-10-26 (UTC)**; 47.5 % missing |
| `nitrogen_dioxide` | NO2 | µg/m³ | complete |
| `sulphur_dioxide` | SO2 | µg/m³ | complete |
| `ozone` | O3 | µg/m³ | complete |
| `dust` | Mineral (desert) dust | µg/m³ | complete; 0 in ~78 % of hours |
| `aerosol_optical_depth` | AOD at 550 nm | dimensionless | complete |
| `us_aqi` | US AQI (derived from the pollutants) | index | complete |

### Weather (11 variables)

| API name | Meaning | Raw unit | Unit after cleaning | Availability |
|---|---|---|---|---|
| `temperature_2m` | Air temperature at 2 m | °C | °C | complete |
| `relative_humidity_2m` | Relative humidity at 2 m | % | % | complete |
| `dew_point_2m` | Dew point at 2 m | °C | °C | complete |
| `precipitation` | Rain + showers in the preceding hour | mm | mm/h | complete |
| `surface_pressure` | Pressure at surface | hPa | hPa | complete |
| `cloud_cover` | Total cloud cover | % | % | complete |
| `wind_speed_10m` | Wind speed at 10 m | km/h | **m/s** | complete |
| `wind_direction_10m` | Wind direction at 10 m | ° | ° | complete (circular: excluded from means/correlations) |
| `wind_gusts_10m` | Gusts at 10 m | km/h | **m/s** | complete |
| `shortwave_radiation` | Solar radiation (preceding-hour mean) | W/m² | W/m² | complete |
| `boundary_layer_height` | Mixing-layer height | m | m | **missing 2024-01-01 to 2024-06-30**; 13 % |

Note vs. the proposal: the proposal lists PM10, PM2.5, CO, CO2 and dust. NO2, SO2, O3, AOD
and US AQI were added because they are free in the same call and useful for the correlation
heatmap. CO2 only covers about half of the period, so any CO2 chart must show its coverage.

## 5. Period

- Raw (UTC): 2022-12-31 00:00 to 2026-10-31 23:00, 33,624 hours per city.
- Analysis window (UTC+7): 2023-01-01 00:00 to 2026-10-31 23:00, 33,600 hours (1,400 days)
  per city. Nearly four years gives 3-4 repetitions of every season for the
  "what patterns repeat" question.

## 6. Provenance fields

Every row carries `aq_source`, `weather_source` and `data_type = "modelled"` so tooltips
can show the "modelled data" label required by the must-have features.
