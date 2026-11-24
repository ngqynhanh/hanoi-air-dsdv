"""Week 2 - Clean both datasets, convert to Vietnam time and merge them.

Rules (proposal section 3.2):
  * duplicates removed; city names and units standardized
  * timestamps converted from UTC to Vietnam local time (UTC+7)
  * missing / invalid values are FLAGGED and left as NaN, never replaced by 0
  * unusually high pollution values are FLAGGED for review, never removed
  * air-quality and weather joined on (city, timestamp), completeness checked

Output:
  data/clean/air_quality_clean.csv, weather_clean.csv, merged_hourly.csv
  data/clean/outlier_review.csv      one row per (city, variable, day) with flagged hours
  docs/cleaning_report.md
Run:  python scripts/03_clean_merge.py
"""
import pandas as pd

import config as C

ALIASES = {a.lower(): city for city, info in C.CITIES.items()
           for a in [city, *info["aliases"]]}


def standardize_city(name: str) -> str:
    key = str(name).strip().lower()
    if key not in ALIASES:
        raise ValueError(f"Unknown city name: {name!r}")
    return ALIASES[key]


def clean(kind: str, variables: list, log: list) -> pd.DataFrame:
    files = sorted(C.RAW_DIR.glob(f"{kind}_*.csv"))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    n_raw = len(df)

    # City names
    df["city"] = df["city"].map(standardize_city)

    # Timestamps: raw is UTC -> timezone-aware -> Vietnam local time
    utc = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M", errors="coerce", utc=True)
    n_bad_time = int(utc.isna().sum())
    df = df.loc[utc.notna()].copy()
    df["datetime_utc"] = utc.dropna()
    df["datetime_local"] = df["datetime_utc"].dt.tz_convert(C.LOCAL_TZ)

    # Duplicates (same city + timestamp): keep the first occurrence
    n_dup = int(df.duplicated(["city", "datetime_utc"]).sum())
    df = df.drop_duplicates(["city", "datetime_utc"])

    # Restrict to the analysis window (complete local days)
    start = pd.Timestamp(C.LOCAL_START, tz=C.LOCAL_TZ)
    end = pd.Timestamp(C.LOCAL_END, tz=C.LOCAL_TZ)
    df = df[(df["datetime_local"] >= start) & (df["datetime_local"] <= end)]

    # Re-index on the full hourly grid so absent timestamps become explicit NaN rows
    full = pd.MultiIndex.from_product(
        [list(C.CITIES), pd.date_range(start, end, freq="h")],
        names=["city", "datetime_local"])
    n_before = len(df)
    df = df.set_index(["city", "datetime_local"])[variables].reindex(full).reset_index()
    n_added = len(df) - n_before

    # Units: wind km/h -> m/s (all other raw units are already the target units)
    for v in ("wind_speed_10m", "wind_gusts_10m"):
        if v in df:
            df[v] = (df[v] / 3.6).round(2)

    # Invalid values -> NaN + flag
    invalid = pd.Series("", index=df.index)
    n_invalid = {}
    for v in variables:
        df[v] = pd.to_numeric(df[v], errors="coerce")
        lo, hi = C.VALID_RANGES[v]
        bad = (df[v] < lo) | (df[v] > hi)
        if bad.any():
            n_invalid[v] = int(bad.sum())
            invalid = invalid.where(~bad, invalid + v + ";")
            df.loc[bad, v] = float("nan")

    # Missing values -> flag only
    missing = pd.Series("", index=df.index)
    n_missing = {}
    for v in variables:
        na = df[v].isna()
        if na.any():
            n_missing[v] = int(na.sum())
            missing = missing.where(~na, missing + v + ";")

    # Unusually high pollution -> flag for review (per city, Q3 + 3*IQR)
    outlier = pd.Series("", index=df.index)
    thresholds = []
    for v in [x for x in variables if x in C.OUTLIER_VARS]:
        for city, g in df.groupby("city", sort=False):
            s = g[v].dropna()
            if v == "dust":  # zero-inflated: use non-zero hours for the threshold
                s = s[s > 0]
            q1, q3 = s.quantile([.25, .75])
            thr = q3 + 3 * (q3 - q1)
            hit = (df["city"] == city) & (df[v] > thr)
            outlier = outlier.where(~hit, outlier + v + ";")
            thresholds.append({"variable": v, "city": city, "threshold": round(thr, 1),
                               "n_flagged": int(hit.sum()),
                               "pct_flagged": round(100 * hit.sum() / len(g), 2),
                               "max": g[v].max()})

    suffix = "aq" if kind == "air_quality" else "wx"
    df[f"{suffix}_missing"] = missing.str.rstrip(";")
    df[f"{suffix}_invalid"] = invalid.str.rstrip(";")
    if kind == "air_quality":
        df["aq_outlier"] = outlier.str.rstrip(";")

    log.append({"dataset": kind, "raw_rows": n_raw, "unparseable_timestamps": n_bad_time,
                "duplicates_removed": n_dup, "rows_in_window": n_before,
                "missing_timestamps_added": n_added, "clean_rows": len(df),
                "invalid": n_invalid, "missing": n_missing, "thresholds": thresholds})
    return df


def outlier_review(aq: pd.DataFrame) -> pd.DataFrame:
    """Daily summary of flagged hours so each episode can be reviewed by eye."""
    rows = []
    date = aq["datetime_local"].dt.date
    for v in C.OUTLIER_VARS:
        hit = aq["aq_outlier"].str.split(";").map(lambda xs: v in xs)
        g = aq[hit].groupby(["city", date[hit]])[v].agg(["count", "max", "mean"])
        g = g.reset_index().rename(columns={"datetime_local": "date", "count": "flagged_hours",
                                            "max": "max_value", "mean": "mean_flagged_value"})
        g.insert(1, "variable", v)
        rows.append(g)
    out = pd.concat(rows, ignore_index=True)
    out["mean_flagged_value"] = out["mean_flagged_value"].round(1)
    return out.sort_values(["variable", "max_value"], ascending=[True, False])


def write_csv(df: pd.DataFrame, path):
    out = df.copy()
    # ISO 8601 with explicit +07:00 offset keeps the timezone unambiguous
    out["datetime_local"] = out["datetime_local"].dt.strftime("%Y-%m-%dT%H:%M:%S%z").str.replace(
        r"(\+\d{2})(\d{2})$", r"\1:\2", regex=True)
    out.to_csv(path, index=False, encoding="utf-8")


def main():
    C.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    C.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    log = []
    aq = clean("air_quality", C.AQ_VARS, log)
    wx = clean("weather", C.WEATHER_VARS, log)

    # Join on city + timestamp; outer join + indicator exposes one-sided records
    merged = aq.merge(wx, on=["city", "datetime_local"], how="outer", indicator=True)
    join_counts = merged["_merge"].value_counts().to_dict()
    merged["has_air_quality"] = merged["_merge"].isin(["both", "left_only"])
    merged["has_weather"] = merged["_merge"].isin(["both", "right_only"])
    merged = merged.drop(columns="_merge")
    for c in ("aq_missing", "aq_invalid", "aq_outlier", "wx_missing", "wx_invalid"):
        merged[c] = merged[c].fillna("")
    merged["latitude"] = merged["city"].map(lambda c: C.CITIES[c]["lat"])
    merged["longitude"] = merged["city"].map(lambda c: C.CITIES[c]["lon"])
    merged["aq_source"] = C.AQ_SOURCE
    merged["weather_source"] = C.WEATHER_SOURCE
    merged["data_type"] = C.DATA_TYPE
    merged = merged.sort_values(["city", "datetime_local"]).reset_index(drop=True)
    front = ["city", "latitude", "longitude", "datetime_local"]
    merged = merged[front + [c for c in merged.columns if c not in front]]

    review = outlier_review(aq)
    write_csv(aq, C.CLEAN_DIR / "air_quality_clean.csv")
    write_csv(wx, C.CLEAN_DIR / "weather_clean.csv")
    write_csv(merged, C.CLEAN_DIR / "merged_hourly.csv")
    review.to_csv(C.CLEAN_DIR / "outlier_review.csv", index=False, encoding="utf-8")

    # ---- report ----
    complete = (merged.groupby("city", sort=False)
                .agg(hours=("datetime_local", "size"),
                     first=("datetime_local", "min"), last=("datetime_local", "max"),
                     with_air_quality=("has_air_quality", "sum"),
                     with_weather=("has_weather", "sum"),
                     pm2_5_available=("pm2_5", "count"),
                     all_core_vars_available=("pm2_5", lambda s: int(
                         merged.loc[s.index, ["pm2_5", "pm10", "temperature_2m",
                                              "relative_humidity_2m", "wind_speed_10m"]]
                         .notna().all(axis=1).sum())))
                .reset_index())
    lines = ["# Cleaning and merge report\n",
             "_Generated by `scripts/03_clean_merge.py`._\n",
             f"Analysis window (Vietnam local time, UTC+7): **{C.LOCAL_START}** to "
             f"**{C.LOCAL_END}**.\n", "## Steps per dataset\n"]
    steps = pd.DataFrame([{k: v for k, v in e.items()
                           if k not in ("invalid", "missing", "thresholds")} for e in log])
    lines.append(steps.to_markdown(index=False) + "\n")
    for e in log:
        lines.append(f"### {e['dataset']}\n")
        lines.append(f"- Invalid (out-of-range) values set to NaN and flagged: "
                     f"{e['invalid'] or 'none'}")
        lines.append(f"- Missing values flagged (left as NaN): {e['missing'] or 'none'}\n")
    lines.append("## Unit standardization\n")
    lines.append("- `wind_speed_10m`, `wind_gusts_10m`: km/h -> m/s (divided by 3.6).")
    lines.append("- All other variables are kept in the unit delivered by the API:\n")
    lines.append(pd.DataFrame({"variable": list(C.UNITS), "unit": list(C.UNITS.values())})
                 .to_markdown(index=False) + "\n")
    lines.append("## Unusually high values (flagged in `aq_outlier`, not removed)\n")
    lines.append("Rule: value above the city's own Q3 + 3·IQR for that pollutant "
                 "(dust: computed on non-zero hours).\n")
    lines.append(pd.DataFrame(log[0]["thresholds"]).to_markdown(index=False) + "\n")
    lines.append("Largest flagged episodes (full list in `data/clean/outlier_review.csv`):\n")
    top = (review[review["variable"] == "pm2_5"].head(10))
    lines.append(top.to_markdown(index=False) + "\n")
    lines.append("## Merge and completeness\n")
    lines.append(f"- Join key: `city` + `datetime_local`; outer join result: {join_counts}\n")
    lines.append(complete.to_markdown(index=False) + "\n")
    (C.DOCS_DIR / "cleaning_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"merged_hourly.csv: {merged.shape}; join: {join_counts}")


if __name__ == "__main__":
    main()
