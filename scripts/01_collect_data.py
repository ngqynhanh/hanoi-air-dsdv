"""Week 1 - Collect raw hourly air-quality and weather data from Open-Meteo.

Output (data/raw/):
  air_quality_<city>.csv, weather_<city>.csv   raw values exactly as returned (time in GMT)
  collection_metadata.json                     endpoints, units, grid cells, retrieval time
Run:  python scripts/01_collect_data.py
"""
import json
import time
from datetime import datetime, timezone

import pandas as pd
import requests

import config as C


def year_chunks(start: str, end: str):
    """Split [start, end] into calendar-year pieces to keep each request small."""
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    for year in range(s.year, e.year + 1):
        a = max(s, pd.Timestamp(year=year, month=1, day=1))
        b = min(e, pd.Timestamp(year=year, month=12, day=31))
        yield a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")


def fetch(endpoint: str, params: dict, retries: int = 5) -> dict:
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(endpoint, params=params, timeout=120)
            if r.status_code == 200:
                return r.json()
            reason = r.text[:200]
        except requests.RequestException as exc:
            reason = str(exc)
        wait = 15 * attempt  # also covers HTTP 429 (rate limit)
        print(f"    attempt {attempt} failed ({reason}); retrying in {wait}s")
        time.sleep(wait)
    raise RuntimeError(f"Request failed after {retries} attempts: {endpoint} {params}")


def collect(kind: str, endpoint: str, variables: list, source: str, meta: dict):
    for city, info in C.CITIES.items():
        frames, grid, units = [], None, None
        for start, end in year_chunks(C.FETCH_START_UTC, C.FETCH_END_UTC):
            params = {
                "latitude": info["lat"], "longitude": info["lon"],
                "start_date": start, "end_date": end,
                "hourly": ",".join(variables), "timezone": "GMT",
            }
            data = fetch(endpoint, params)
            frames.append(pd.DataFrame(data["hourly"]))
            grid = {"latitude": data["latitude"], "longitude": data["longitude"],
                    "elevation_m": data.get("elevation")}
            units = data["hourly_units"]
            time.sleep(3)  # stay well under the free-tier rate limit

        df = pd.concat(frames, ignore_index=True)
        df.insert(0, "city", city)
        df.insert(1, "latitude", info["lat"])
        df.insert(2, "longitude", info["lon"])
        df["source"] = source
        df["data_type"] = C.DATA_TYPE
        out = C.RAW_DIR / f"{kind}_{city.lower().replace(' ', '_')}.csv"
        df.to_csv(out, index=False, encoding="utf-8")
        print(f"  [ok] {kind:<11} {city:<17} {len(df):>6} rows -> {out.name}")

        meta[kind]["units"] = units
        meta[kind]["cities"][city] = {
            "requested": {"latitude": info["lat"], "longitude": info["lon"]},
            "grid_cell": grid, "rows": len(df), "file": out.name,
        }


def main():
    C.RAW_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "period_utc": [C.FETCH_START_UTC, C.FETCH_END_UTC],
        "timezone_of_raw_timestamps": "GMT (UTC+0)",
        "air_quality": {"endpoint": C.AQ_ENDPOINT, "source": C.AQ_SOURCE,
                        "data_type": C.DATA_TYPE, "variables": C.AQ_VARS,
                        "units": {}, "cities": {}},
        "weather": {"endpoint": C.WEATHER_ENDPOINT, "source": C.WEATHER_SOURCE,
                    "data_type": C.DATA_TYPE, "variables": C.WEATHER_VARS,
                    "units": {}, "cities": {}},
    }
    print("Collecting air-quality data...")
    collect("air_quality", C.AQ_ENDPOINT, C.AQ_VARS, C.AQ_SOURCE, meta)
    print("Collecting historical weather data...")
    collect("weather", C.WEATHER_ENDPOINT, C.WEATHER_VARS, C.WEATHER_SOURCE, meta)

    with open(C.RAW_DIR / "collection_metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print("Done. Metadata written to collection_metadata.json")


if __name__ == "__main__":
    main()
