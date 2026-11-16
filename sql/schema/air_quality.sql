-- Air quality in India (CPCB data, 2015-2020): stations + daily readings per city and per station.
-- Re-runnable: drops and recreates everything.
CREATE SCHEMA IF NOT EXISTS air_quality;
DROP TABLE IF EXISTS air_quality.station_daily, air_quality.city_daily, air_quality.stations CASCADE;

CREATE TABLE air_quality.stations (
    station_id   TEXT PRIMARY KEY,
    station_name TEXT NOT NULL,
    city         TEXT NOT NULL,
    state        TEXT NOT NULL,
    status       TEXT
);

CREATE TABLE air_quality.city_daily (
    city       TEXT NOT NULL,
    obs_date   DATE NOT NULL,
    pm25       NUMERIC(8, 2),
    pm10       NUMERIC(8, 2),
    no         NUMERIC(8, 2),
    no2        NUMERIC(8, 2),
    nox        NUMERIC(8, 2),
    nh3        NUMERIC(8, 2),
    co         NUMERIC(8, 2),
    so2        NUMERIC(8, 2),
    o3         NUMERIC(8, 2),
    benzene    NUMERIC(8, 2),
    toluene    NUMERIC(8, 2),
    xylene     NUMERIC(8, 2),
    aqi        NUMERIC(8, 2),
    aqi_bucket TEXT,
    PRIMARY KEY (city, obs_date)
);

CREATE TABLE air_quality.station_daily (
    station_id TEXT NOT NULL REFERENCES air_quality.stations(station_id),
    obs_date   DATE NOT NULL,
    pm25       NUMERIC(8, 2),
    pm10       NUMERIC(8, 2),
    no         NUMERIC(8, 2),
    no2        NUMERIC(8, 2),
    nox        NUMERIC(8, 2),
    nh3        NUMERIC(8, 2),
    co         NUMERIC(8, 2),
    so2        NUMERIC(8, 2),
    o3         NUMERIC(8, 2),
    benzene    NUMERIC(8, 2),
    toluene    NUMERIC(8, 2),
    xylene     NUMERIC(8, 2),
    aqi        NUMERIC(8, 2),
    aqi_bucket TEXT,
    PRIMARY KEY (station_id, obs_date)
);

CREATE INDEX idx_city_daily_date    ON air_quality.city_daily (obs_date);
CREATE INDEX idx_station_daily_date ON air_quality.station_daily (obs_date);
CREATE INDEX idx_stations_city      ON air_quality.stations (city);

COMMENT ON TABLE air_quality.stations IS 'Air-quality monitoring stations run by Indian pollution control boards';
COMMENT ON COLUMN air_quality.stations.station_id IS 'Station code, e.g. DL001 (primary key)';
COMMENT ON COLUMN air_quality.stations.station_name IS 'Station name and operating agency';
COMMENT ON COLUMN air_quality.stations.city IS 'City the station is in';
COMMENT ON COLUMN air_quality.stations.state IS 'Indian state the station is in';
COMMENT ON COLUMN air_quality.stations.status IS 'Active, Inactive, or NULL when unknown';

COMMENT ON TABLE air_quality.city_daily IS 'Daily average pollutant readings and AQI per city (26 cities, 2015-01-01 to 2020-07-01). Averages must ignore NULL readings';
COMMENT ON COLUMN air_quality.city_daily.city IS 'City name, e.g. Delhi, Mumbai, Bengaluru';
COMMENT ON COLUMN air_quality.city_daily.obs_date IS 'Date of the reading; month = date_trunc(''month'', obs_date); winter = Nov-Feb';
COMMENT ON COLUMN air_quality.city_daily.pm25 IS 'PM2.5 fine particulate matter, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.pm10 IS 'PM10 particulate matter, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.no IS 'Nitric oxide, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.no2 IS 'Nitrogen dioxide, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.nox IS 'Nitrogen oxides (ppb)';
COMMENT ON COLUMN air_quality.city_daily.nh3 IS 'Ammonia, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.co IS 'Carbon monoxide, milligrams per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.so2 IS 'Sulphur dioxide, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.o3 IS 'Ozone, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.benzene IS 'Benzene, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.toluene IS 'Toluene, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.xylene IS 'Xylene, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.city_daily.aqi IS 'Air Quality Index (higher = worse); NULL when not computed';
COMMENT ON COLUMN air_quality.city_daily.aqi_bucket IS 'AQI category: Good (0-50), Satisfactory (51-100), Moderate (101-200), Poor (201-300), Very Poor (301-400), Severe (401+)';

COMMENT ON TABLE air_quality.station_daily IS 'Daily average pollutant readings and AQI per monitoring station (same columns as city_daily)';
COMMENT ON COLUMN air_quality.station_daily.station_id IS 'Foreign key to air_quality.stations.station_id';
COMMENT ON COLUMN air_quality.station_daily.obs_date IS 'Date of the reading';
COMMENT ON COLUMN air_quality.station_daily.pm25 IS 'PM2.5 fine particulate matter, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.pm10 IS 'PM10 particulate matter, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.no IS 'Nitric oxide, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.no2 IS 'Nitrogen dioxide, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.nox IS 'Nitrogen oxides (ppb)';
COMMENT ON COLUMN air_quality.station_daily.nh3 IS 'Ammonia, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.co IS 'Carbon monoxide, milligrams per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.so2 IS 'Sulphur dioxide, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.o3 IS 'Ozone, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.benzene IS 'Benzene, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.toluene IS 'Toluene, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.xylene IS 'Xylene, micrograms per cubic metre';
COMMENT ON COLUMN air_quality.station_daily.aqi IS 'Air Quality Index (higher = worse); NULL when not computed';
COMMENT ON COLUMN air_quality.station_daily.aqi_bucket IS 'AQI category: Good, Satisfactory, Moderate, Poor, Very Poor, Severe';
