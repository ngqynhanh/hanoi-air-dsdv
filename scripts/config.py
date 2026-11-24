"""Shared configuration for the AirLens data pipeline (Week 1-2 data tasks)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
PROCESSED_DIR = ROOT / "data" / "processed"
DOCS_DIR = ROOT / "docs"

# City centre coordinates (WGS84). Keys are the standardized city names used
# everywhere downstream; "aliases" lists spellings that are mapped onto them.
CITIES = {
    "Hanoi": {"lat": 21.0285, "lon": 105.8542,
              "aliases": ["Ha Noi", "Hà Nội", "hanoi", "HN"]},
    "Ho Chi Minh City": {"lat": 10.8231, "lon": 106.6297,
                         "aliases": ["HCMC", "Ho Chi Minh", "Hồ Chí Minh", "TP.HCM", "Saigon"]},
    "Da Nang": {"lat": 16.0544, "lon": 108.2022,
                "aliases": ["Danang", "Đà Nẵng", "DN"]},
    "Hai Phong": {"lat": 20.8449, "lon": 106.6881,
                  "aliases": ["Haiphong", "Hải Phòng", "HP"]},
}

# The APIs are queried in UTC (GMT). We fetch one extra day at the start so
# that, after converting to UTC+7, the analysis window is made of complete
# local days: 2023-01-01 00:00 .. 2026-10-31 23:00 (Asia/Ho_Chi_Minh).
FETCH_START_UTC = "2022-12-31"
FETCH_END_UTC = "2026-10-31"
LOCAL_TZ = "Asia/Ho_Chi_Minh"
LOCAL_START = "2023-01-01 00:00"
LOCAL_END = "2026-10-31 23:00"

AQ_ENDPOINT = "https://air-quality-api.open-meteo.com/v1/air-quality"
WEATHER_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"

AQ_VARS = [
    "pm2_5", "pm10", "carbon_monoxide", "carbon_dioxide", "nitrogen_dioxide",
    "sulphur_dioxide", "ozone", "dust", "aerosol_optical_depth", "us_aqi",
]
WEATHER_VARS = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "precipitation",
    "surface_pressure", "cloud_cover", "wind_speed_10m", "wind_direction_10m",
    "wind_gusts_10m", "shortwave_radiation", "boundary_layer_height",
]

AQ_SOURCE = "open-meteo-air-quality/CAMS-global"
WEATHER_SOURCE = "open-meteo-archive/reanalysis-best-match"
DATA_TYPE = "modelled"  # both sources are model/reanalysis output, not station measurements

# Units after cleaning (wind is converted from km/h to m/s in 03_clean_merge.py).
UNITS = {
    "pm2_5": "µg/m³", "pm10": "µg/m³", "carbon_monoxide": "µg/m³",
    "carbon_dioxide": "ppm", "nitrogen_dioxide": "µg/m³",
    "sulphur_dioxide": "µg/m³", "ozone": "µg/m³", "dust": "µg/m³",
    "aerosol_optical_depth": "dimensionless", "us_aqi": "US AQI index",
    "temperature_2m": "°C", "relative_humidity_2m": "%", "dew_point_2m": "°C",
    "precipitation": "mm/h", "surface_pressure": "hPa", "cloud_cover": "%",
    "wind_speed_10m": "m/s", "wind_direction_10m": "° (from north)",
    "wind_gusts_10m": "m/s", "shortwave_radiation": "W/m²",
    "boundary_layer_height": "m",
}

# Physically valid ranges; values outside are flagged invalid and set to NaN.
VALID_RANGES = {
    "pm2_5": (0, 2000), "pm10": (0, 5000), "carbon_monoxide": (0, 100000),
    "carbon_dioxide": (300, 1000), "nitrogen_dioxide": (0, 2000),
    "sulphur_dioxide": (0, 5000), "ozone": (0, 1000), "dust": (0, 10000),
    "aerosol_optical_depth": (0, 10), "us_aqi": (0, 1000),
    "temperature_2m": (-10, 50), "relative_humidity_2m": (0, 100),
    "dew_point_2m": (-30, 40), "precipitation": (0, 300),
    "surface_pressure": (800, 1100), "cloud_cover": (0, 100),
    "wind_speed_10m": (0, 100), "wind_direction_10m": (0, 360),
    "wind_gusts_10m": (0, 120), "shortwave_radiation": (0, 1500),
    "boundary_layer_height": (0, 10000),
}

# Pollutants whose unusually high values are flagged for review (never removed).
OUTLIER_VARS = ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide",
                "sulphur_dioxide", "ozone", "dust"]

WHO_PM25_24H = 15.0  # µg/m³, WHO 2021 24-hour guideline
