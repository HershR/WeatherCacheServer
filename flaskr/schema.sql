
DROP TABLE IF EXISTS owm_cities;
DROP TABLE IF EXISTS owm_current_weather;
DROP TABLE IF EXISTS owm_hourly_weather_forecast;

CREATE TABLE owm_cities (
  city_id INTEGER PRIMARY KEY AUTOINCREMENT,
  city_name TEXT NOT NULL,
  city_coord_long REAL NOT NULL,
  city_coord_lat REAL NOT NULL,
  city_country TEXT NOT NULL
);

-- ALL TIME RELATED FIELD IN UTC --
CREATE TABLE owm_current_weather (
  timestamp INT DEFAULT (cast(strftime('%s','now') as int)),
  city_id INTEGER NOT NULL,
  city_sun_rise INTEGER NOT NULL,
  city_sun_set INTEGER NOT NULL,
  timezone_offset INT NOT NULL, --timezone offset from UTC
  temperature_value REAL NOT NULL,
  temperature_min REAL NOT NULL,
  temperature_max REAL NOT NULL,
  temperature_unit TEXT DEFAULT "C", --default Celsius
  feels_like_value REAL NOT NULL,
  feels_like_unit TEXT DEFAULT "C",
  humidity_value INTEGER NOT NULL,
  humidity_unit TEXT DEFAULT "%",
  pressure_value INTEGER NOT NULL,
  pressure_unit TEXT DEFAULT "hPa", --default hPa
  wind_speed_value REAL NOT NULL,
  wind_speed_unit TEXT DEFAULT "m/s", --default meter/sec
  wind_speed_name TEXT NOT NULL,
  wind_direction_value_deg INTEGER NOT NULL, --in degrees
  wind_direction_code TEXT NOT NULL,
  wind_direction_name TEXT NOT NULL,
  clouds_value_pct REAL NOT NULL, --Cloudiness %
  clouds_name TEXT DEFAULT "None",
  visibility_value_m INTEGER NOT NULL, -- in meters
  precipitation_value_mm REAL NOT NULL, --rain volume in millimeters
  precipitation_mode TEXT NOT NULL DEFAULT "no", -- no or rain or snow
  weather_number INTEGER NOT NULL,
  weather_value TEXT NOT NULL,
  weather_icon TEXT NOT NULL,
  lastupdate_value TEXT DEFAULT "None",
  FOREIGN KEY (city_id) REFERENCES owm_cities (city_id)
);

CREATE TABLE owm_hourly_weather_forecast (
  request_timestamp INT DEFAULT (cast(strftime('%s','now') as int)),
  forecast_timestamp TEXT NOT NULL,
  city_id INTEGER NOT NULL,
  city_sun_rise INTEGER NOT NULL,
  city_sun_set INTEGER NOT NULL,
  timezone_offset INT NOT NULL, --timezone offset from UTC
  temperature_value REAL NOT NULL,
  temperature_min REAL NOT NULL,
  temperature_max REAL NOT NULL,
  temperature_unit TEXT DEFAULT "C", --default Celsius
  feels_like_value REAL NOT NULL,
  feels_like_unit TEXT DEFAULT "C",
  humidity_value INTEGER NOT NULL,
  humidity_unit TEXT DEFAULT "%",
  pressure_value INTEGER NOT NULL,
  pressure_unit TEXT DEFAULT "hPa", --default hPa
  wind_speed_value REAL NOT NULL,
  wind_speed_unit TEXT DEFAULT "m/s", --default meter/sec
  wind_speed_name TEXT NOT NULL,
  wind_direction_value_deg INTEGER NOT NULL, --in degrees
  wind_direction_code TEXT NOT NULL,
  wind_direction_name TEXT NOT NULL,
  clouds_value_pct REAL NOT NULL, --Cloudiness %
  clouds_name TEXT DEFAULT "None",
  visibility_value_m INTEGER NOT NULL, -- in meters
  precipitation_value_mm REAL NOT NULL DEFAULT 0, --rain volume in millimeters
  precipitation_mode TEXT NOT NULL DEFAULT "no", -- no or rain or snow
  weather_number INTEGER NOT NULL,
  weather_value TEXT NOT NULL,
  weather_icon TEXT NOT NULL,
  lastupdate_value TEXT DEFAULT "None",
  FOREIGN KEY (city_id) REFERENCES owm_cities (city_id)
);