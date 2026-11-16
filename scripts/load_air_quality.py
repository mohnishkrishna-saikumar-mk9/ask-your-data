"""Load daily air-quality data into the `air_quality` schema - the time-series test.

Run from the project root:  python -m scripts.load_air_quality
Expects data/raw/air_quality/{city_day,station_day,stations}.csv (Kaggle "Air Quality Data in India").
The two *_hour.csv files are deliberately NOT loaded: daily data answers every question we need.
"""
from pathlib import Path

import pandas as pd

from scripts._loader_utils import RAW_DIR, load_tables, null_report, read_csv, rows_report

POLLUTANTS = {
    "PM2.5": "pm25", "PM10": "pm10", "NO": "no", "NO2": "no2", "NOx": "nox", "NH3": "nh3",
    "CO": "co", "SO2": "so2", "O3": "o3", "Benzene": "benzene", "Toluene": "toluene",
    "Xylene": "xylene", "AQI": "aqi", "AQI_Bucket": "aqi_bucket",
}
STATION_COLS = {"StationId": "station_id", "StationName": "station_name", "City": "city",
                "State": "state", "Status": "status"}


def clean_daily(raw: pd.DataFrame, key_col: str, key_name: str) -> pd.DataFrame:
    """Rename pollutant columns, parse dates and numbers. Missing readings stay NULL."""
    df = raw.rename(columns={**POLLUTANTS, key_col: key_name, "Date": "obs_date"})
    df["obs_date"] = pd.to_datetime(df["obs_date"], format="%Y-%m-%d").dt.date
    numeric = [c for c in POLLUTANTS.values() if c != "aqi_bucket"]
    df[numeric] = df[numeric].apply(pd.to_numeric)
    return df[[key_name, "obs_date", *POLLUTANTS.values()]]


def main(raw_dir: Path = RAW_DIR / "air_quality") -> None:
    print("Loading air quality ...")
    raw_stations = read_csv(raw_dir / "stations.csv")
    raw_city = read_csv(raw_dir / "city_day.csv")
    raw_station_day = read_csv(raw_dir / "station_day.csv")

    stations = raw_stations.rename(columns=STATION_COLS)[list(STATION_COLS.values())]
    city_daily = clean_daily(raw_city, "City", "city")
    station_daily = clean_daily(raw_station_day, "StationId", "station_id")
    station_daily = station_daily[station_daily["station_id"].isin(stations["station_id"])]

    rows_report("stations", len(raw_stations), len(stations))
    rows_report("city_daily", len(raw_city), len(city_daily))
    rows_report("station_daily", len(raw_station_day), len(station_daily))
    null_report(city_daily, "city_daily")
    load_tables("air_quality.sql", [("air_quality.stations", stations),
                                    ("air_quality.city_daily", city_daily),
                                    ("air_quality.station_daily", station_daily)])


if __name__ == "__main__":
    main()
