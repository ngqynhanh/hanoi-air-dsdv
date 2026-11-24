"""Week 2 - Time variables, daily/monthly statistics and correlations.

Output (data/processed/):
  hourly_processed.csv        merged hourly data + time variables
  daily_stats.csv             city x date x variable: mean, max, min, n_obs, coverage_pct
  monthly_stats.csv           city x year-month x variable: same statistics
  hour_dow_pm25.csv           city x day-of-week x hour mean PM2.5 (heatmap input)
  city_summary.csv            summary cards per city (mean PM2.5, WHO exceedance, worst hour/month)
  correlations_long.csv       every variable pair: city, level, method, r, n
  correlation_matrix_<city>.csv   Pearson matrix on hourly data (heatmap input)
docs/summary_statistics.md, docs/correlation_notes.md
Run:  python scripts/04_process_stats.py
"""
import numpy as np
import pandas as pd

import config as C

VARS = C.AQ_VARS + C.WEATHER_VARS
# wind direction is circular (0 deg = 360 deg) so linear statistics are meaningless for it
STAT_VARS = [v for v in VARS if v != "wind_direction_10m"]
CORR_VARS = STAT_VARS
SUM_VARS = {"precipitation"}  # reported additionally as a total


def add_time_variables(df: pd.DataFrame) -> pd.DataFrame:
    t = df["datetime_local"]
    df["date"] = t.dt.strftime("%Y-%m-%d")
    df["year"] = t.dt.year
    df["month"] = t.dt.month
    df["year_month"] = t.dt.strftime("%Y-%m")
    df["day"] = t.dt.day
    df["hour"] = t.dt.hour
    df["day_of_week"] = t.dt.dayofweek  # 0 = Monday
    df["day_name"] = t.dt.day_name()
    df["is_weekend"] = (t.dt.dayofweek >= 5).astype(int)
    df["week_of_year"] = t.dt.isocalendar().week.astype(int)
    df["season"] = df["month"].map(
        {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring",
         6: "Summer", 7: "Summer", 8: "Summer", 9: "Autumn", 10: "Autumn", 11: "Autumn"})
    df["time_of_day"] = pd.cut(df["hour"], [-1, 5, 11, 17, 23],
                               labels=["Night", "Morning", "Afternoon", "Evening"])
    return df


def aggregate(df: pd.DataFrame, period: str) -> pd.DataFrame:
    """Long table: mean / max / min / observation count / coverage per variable."""
    expected = df.groupby(["city", period]).size().rename("expected_hours")
    g = df.groupby(["city", period], sort=True)[STAT_VARS]
    wide = pd.concat({"mean": g.mean(), "max": g.max(), "min": g.min(),
                      "n_obs": g.count()}, axis=1)
    out = wide.stack(level=1, future_stack=True).rename_axis(
        ["city", period, "variable"]).reset_index()
    out = out.merge(expected.reset_index(), on=["city", period])
    out["coverage_pct"] = (100 * out["n_obs"] / out["expected_hours"]).round(1)
    out[["mean", "max", "min"]] = out[["mean", "max", "min"]].round(2)
    out["unit"] = out["variable"].map(C.UNITS)
    return out


def correlations(df: pd.DataFrame, level: str) -> pd.DataFrame:
    rows = []
    groups = [("All cities", df)] + list(df.groupby("city", sort=False))
    for city, g in groups:
        x = g[CORR_VARS]
        n = x.notna().astype(int).T @ x.notna().astype(int)  # pairwise sample size
        for method in ("pearson", "spearman"):
            m = x.corr(method=method)
            for i, a in enumerate(CORR_VARS):
                for b in CORR_VARS[i + 1:]:
                    rows.append({"city": city, "level": level, "method": method,
                                 "var_x": a, "var_y": b, "r": round(m.loc[a, b], 4),
                                 "n": int(n.loc[a, b])})
    return pd.DataFrame(rows)


def main():
    C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    flag_cols = ["aq_missing", "aq_invalid", "aq_outlier", "wx_missing", "wx_invalid",
                 "aq_source", "weather_source", "data_type"]
    df = pd.read_csv(C.CLEAN_DIR / "merged_hourly.csv",
                     dtype={**{c: "category" for c in flag_cols},
                            **{v: "float32" for v in VARS}})  # keeps memory use low
    # all timestamps share the +07:00 offset, so parsing keeps them as local wall time
    df["datetime_local"] = pd.to_datetime(df["datetime_local"].str.slice(0, 19))
    df = add_time_variables(df)
    df.to_csv(C.PROCESSED_DIR / "hourly_processed.csv", index=False, encoding="utf-8",
              date_format="%Y-%m-%dT%H:%M:%S+07:00")

    # ---- daily / monthly statistics ----
    daily = aggregate(df, "date")
    monthly = aggregate(df, "year_month")
    daily.to_csv(C.PROCESSED_DIR / "daily_stats.csv", index=False, encoding="utf-8")
    monthly.to_csv(C.PROCESSED_DIR / "monthly_stats.csv", index=False, encoding="utf-8")

    # ---- hour x day-of-week heatmap input ----
    hd = (df.groupby(["city", "day_of_week", "day_name", "hour"])["pm2_5"]
            .agg(mean_pm2_5="mean", n_obs="count").round(2).reset_index())
    hd.to_csv(C.PROCESSED_DIR / "hour_dow_pm25.csv", index=False, encoding="utf-8")

    # ---- summary cards per city ----
    d25 = daily[daily["variable"] == "pm2_5"]
    m25 = monthly[monthly["variable"] == "pm2_5"]
    cards = []
    for city, g in df.groupby("city", sort=False):
        dd, mm = d25[d25["city"] == city], m25[m25["city"] == city]
        by_hour = g.groupby("hour")["pm2_5"].mean()
        by_month = g.groupby("month")["pm2_5"].mean()
        worst_m = mm.loc[mm["mean"].idxmax()]
        worst_d = dd.loc[dd["mean"].idxmax()]
        cards.append({
            "city": city, "hours": len(g), "pm2_5_n_obs": int(g["pm2_5"].count()),
            "pm2_5_mean": round(g["pm2_5"].mean(), 1),
            "pm2_5_median": round(g["pm2_5"].median(), 1),
            "pm2_5_max_hourly": g["pm2_5"].max(),
            "days_above_who_24h_pct": round(100 * (dd["mean"] > C.WHO_PM25_24H).mean(), 1),
            "hours_above_15ug_pct": round(100 * (g["pm2_5"] > C.WHO_PM25_24H).mean(), 1),
            "worst_hour_of_day": int(by_hour.idxmax()),
            "best_hour_of_day": int(by_hour.idxmin()),
            "worst_calendar_month": int(by_month.idxmax()),
            "best_calendar_month": int(by_month.idxmin()),
            "worst_month": worst_m["year_month"], "worst_month_mean": worst_m["mean"],
            "worst_day": worst_d["date"], "worst_day_mean": worst_d["mean"],
        })
    cards = pd.DataFrame(cards).sort_values("pm2_5_mean", ascending=False)
    num = cards.select_dtypes("floating").columns  # float32 -> float64 for clean output
    cards[num] = cards[num].astype("float64").round(1)
    cards.to_csv(C.PROCESSED_DIR / "city_summary.csv", index=False, encoding="utf-8")

    # ---- correlations ----
    daily_wide = df.groupby(["city", "date"], sort=False)[CORR_VARS].mean().reset_index()
    corr = pd.concat([correlations(df, "hourly"), correlations(daily_wide, "daily_mean")],
                     ignore_index=True)
    corr.to_csv(C.PROCESSED_DIR / "correlations_long.csv", index=False, encoding="utf-8")
    for city, g in [("All cities", df)] + list(df.groupby("city", sort=False)):
        name = city.lower().replace(" ", "_")
        g[CORR_VARS].corr().round(4).to_csv(
            C.PROCESSED_DIR / f"correlation_matrix_{name}.csv", encoding="utf-8")

    # ---- docs ----
    monthly_pm = (m25.assign(month=m25["year_month"].str[5:].astype(int))
                  .groupby(["month", "city"])["mean"].mean().unstack().round(1).reset_index())
    cov = (monthly.groupby("variable")["coverage_pct"].agg(["min", "mean"]).round(1)
           .reindex(STAT_VARS).reset_index())
    stats = [
        "# Summary statistics\n", "_Generated by `scripts/04_process_stats.py`._\n",
        f"Period: {C.LOCAL_START} to {C.LOCAL_END} (UTC+7). WHO 24-hour PM2.5 guideline: "
        f"{C.WHO_PM25_24H} µg/m³. All values are modelled (CAMS / ECMWF reanalysis), not station "
        "measurements.\n",
        "## City summary (PM2.5, µg/m³)\n", cards.set_index("city").T.reset_index().to_markdown(
            index=False, headers=["metric", *cards["city"]]) + "\n",
        "## Mean PM2.5 by calendar month (average of monthly means)\n",
        monthly_pm.to_markdown(index=False) + "\n",
        "## Data coverage of monthly statistics (% of expected hours)\n",
        cov.to_markdown(index=False) + "\n",
        f"Rows: daily_stats {len(daily):,}; monthly_stats {len(monthly):,}.\n",
    ]
    (C.DOCS_DIR / "summary_statistics.md").write_text("\n".join(stats), encoding="utf-8")

    def ranked(city):
        c = corr[(corr["city"] == city) & (corr["level"] == "hourly")]
        c = c[(c["var_x"] == "pm2_5") | (c["var_y"] == "pm2_5")].copy()
        c["variable"] = np.where(c["var_x"] == "pm2_5", c["var_y"], c["var_x"])
        t = c.pivot(index="variable", columns="method", values="r")
        t["n"] = c.groupby("variable")["n"].first()
        return t.reindex(t["pearson"].abs().sort_values(ascending=False).index).reset_index()

    weather_cmp = corr[(corr["level"] == "hourly") & (corr["method"] == "spearman")
                       & (corr["var_x"] == "pm2_5") & corr["var_y"].isin(C.WEATHER_VARS)]
    weather_cmp = weather_cmp.pivot(index="var_y", columns="city", values="r").reset_index()
    notes = [
        "# Correlation analysis notes\n", "_Generated by `scripts/04_process_stats.py`._\n",
        "Files: `correlations_long.csv` (all pairs; Pearson and Spearman; hourly and "
        "daily-mean level; per city and pooled) and `correlation_matrix_<city>.csv` "
        "(Pearson, hourly). `wind_direction_10m` is excluded because it is circular.\n",
        "## Hanoi: PM2.5 vs. every other variable (hourly, ranked by |Pearson r|)\n",
        ranked("Hanoi").to_markdown(index=False, floatfmt=".3f") + "\n",
        "## PM2.5 vs. weather by city (hourly, Spearman)\n",
        weather_cmp.to_markdown(index=False, floatfmt=".3f") + "\n",
        "## Interpretation limits\n",
        "1. **Correlation is not causation.** A coefficient describes how two series move "
        "together; it does not show that one drives the other. Weather, emissions and "
        "pollutant levels share common drivers (season, time of day, monsoon regime).",
        "2. **Confounding by season and daily cycle.** E.g. temperature and PM2.5 are both "
        "seasonal in Hanoi; a negative r mostly reflects winter vs. summer, not a direct "
        "effect of temperature. Compare within a season or use daily means before drawing "
        "conclusions.",
        "3. **Modelled data.** Pollutants (CAMS) and weather (ECMWF reanalysis) come from models, and "
        "CAMS itself is driven by meteorological fields, so part of the pollutant-weather "
        "correlation is built into the model rather than observed.",
        "4. **Shared sources among pollutants.** PM2.5, PM10, CO and NO2 are emitted by the "
        "same activities and dispersed by the same air mass; high r among them indicates "
        "common origin/transport, not that one pollutant produces another. PM2.5 is also a "
        "subset of PM10, and US AQI is computed from the pollutants.",
        "5. **Pearson assumes linearity.** Pollutant distributions are right-skewed and "
        "relations such as wind speed or boundary-layer height vs. PM2.5 are non-linear; "
        "Spearman (rank) values are supplied alongside for that reason.",
        "6. **Autocorrelation.** Hourly values are strongly serially correlated, so the "
        "effective sample size is far below n and p-values would be over-optimistic; they "
        "are therefore not reported.",
        "7. **Unequal samples.** `carbon_dioxide` exists only from 2024-10-26 and "
        "`boundary_layer_height` is missing for 2024-01 to 2024-06; their coefficients use "
        "fewer hours (see column `n`) and a different period.",
        "8. **Spatial scale.** One grid cell (~40 km for CAMS global, ~10-25 km for weather) "
        "represents each city; coefficients describe regional background, not street level.",
        "9. **Pooled ('All cities') coefficients** mix between-city differences with "
        "within-city variation (Simpson's paradox risk); prefer the per-city values.\n",
    ]
    (C.DOCS_DIR / "correlation_notes.md").write_text("\n".join(notes), encoding="utf-8")
    print(f"hourly {df.shape}, daily {daily.shape}, monthly {monthly.shape}, corr {corr.shape}")


if __name__ == "__main__":
    main()
