"""Export compact CSV files for the AirLens dashboard (data/dashboard/).

Run after 04_process_stats.py:  python scripts/05_export_dashboard.py
"""
import pandas as pd

import config as C

OUT = C.ROOT / "data" / "dashboard"
WEATHER = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m",
           "boundary_layer_height", "precipitation"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    P = C.PROCESSED_DIR

    pd.read_csv(P / "city_summary.csv").to_csv(OUT / "city_summary.csv", index=False)

    m = pd.read_csv(P / "monthly_stats.csv")
    m = m[m["variable"] == "pm2_5"][["city", "year_month", "mean", "max", "n_obs", "coverage_pct"]]
    m.to_csv(OUT / "monthly_pm25.csv", index=False)

    pd.read_csv(P / "hour_dow_pm25.csv").to_csv(OUT / "hour_dow_pm25.csv", index=False)

    c = pd.read_csv(P / "correlations_long.csv")
    c = c[c["method"] == "pearson"][["city", "level", "var_x", "var_y", "r", "n"]]
    c["r"] = c["r"].round(3)
    c.to_csv(OUT / "correlations.csv", index=False)

    d = pd.read_csv(P / "daily_stats.csv",
                    usecols=["city", "date", "variable", "mean", "max", "n_obs"])
    d = d[d["variable"].isin(["pm2_5", *WEATHER])]
    pm = d[d["variable"] == "pm2_5"].rename(
        columns={"mean": "pm2_5_mean", "max": "pm2_5_max", "n_obs": "pm2_5_n_obs"})
    pm = pm.drop(columns="variable")
    wx = d[d["variable"].isin(WEATHER)].pivot_table(
        index=["city", "date"], columns="variable", values="mean").reset_index()
    daily = pm.merge(wx, on=["city", "date"], how="left")[
        ["city", "date", "pm2_5_mean", "pm2_5_max", "pm2_5_n_obs", *WEATHER]]
    daily.round(2).to_csv(OUT / "daily.csv", index=False)

    for f in sorted(OUT.glob("*.csv")):
        print(f"{f.name:<20} {f.stat().st_size/1024:8.1f} KB")


if __name__ == "__main__":
    main()
