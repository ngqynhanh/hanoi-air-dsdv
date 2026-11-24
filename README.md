# AirLens - data pipeline (Week 1-2 data tasks)

Install the dependencies with `pip install -r requirements.txt`, then run from the project folder, in order:

```bash
python scripts/01_collect_data.py   # Week 1: download raw air-quality + weather data
python scripts/02_inspect_raw.py    # Week 1: inspect raw data
python scripts/03_clean_merge.py    # Week 2: clean, convert to UTC+7, merge
python scripts/04_process_stats.py  # Week 2: time variables, daily/monthly stats, correlations
```

| Task | Deliverable | Where |
|---|---|---|
| W1 Review API | API/source notes and variable list | `docs/api_source_notes.md` |
| W1 Collect air quality | Raw air-quality datasets | `data/raw/air_quality_<city>.csv` |
| W1 Collect weather | Raw weather datasets | `data/raw/weather_<city>.csv` |
| W1 Inspect | Data inspection summary | `docs/data_inspection_summary.md` |
| W2 Clean | Cleaning script and clean datasets | `scripts/03_clean_merge.py`, `data/clean/*_clean.csv`, `docs/cleaning_report.md`, `data/clean/outlier_review.csv` |
| W2 Timestamps + align | Merged dataset with consistent timestamps | `data/clean/merged_hourly.csv` |
| W2 Time variables + stats | Processed dataset and summary statistics | `data/processed/hourly_processed.csv`, `daily_stats.csv`, `monthly_stats.csv`, `hour_dow_pm25.csv`, `city_summary.csv`, `docs/summary_statistics.md` |
| W2 Correlations | Correlation matrix/data | `data/processed/correlations_long.csv`, `correlation_matrix_<city>.csv`, `docs/correlation_notes.md` |

Settings (cities, period, variables, valid ranges) are in `scripts/config.py`.

Column conventions in the merged/processed files:

- `datetime_local`: ISO 8601 with offset, Vietnam time (`2023-01-01T00:00:00+07:00`).
- `aq_missing`, `wx_missing`, `aq_invalid`, `wx_invalid`, `aq_outlier`: `;`-separated
  variable names flagged in that row (empty = nothing flagged). Missing/invalid values
  stay empty (NaN), they are never replaced by 0; outliers are kept.
- `aq_source`, `weather_source`, `data_type`: provenance (all values are modelled).
- `daily_stats.csv` / `monthly_stats.csv` are long tables: one row per
  city x period x variable with `mean, max, min, n_obs, expected_hours, coverage_pct, unit`.
