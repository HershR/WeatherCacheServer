
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

CREATE TABLE owm_current_weather (
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  city_id INTEGER NOT NULL,
  city_sun_rise INTEGER NOT NULL,
  city_sun_set INTEGER NOT NULL,
  timezone TEXT NOT NULL,
  temperature_value REAL NOT NULL,
  temperature_min REAL NOT NULL,
  temperature_max REAL NOT NULL,
  temperature_unit TEXT DEFAULT "K", --default Kelvin
  feels_like_value REAL NOT NULL,
  feels_like_unit REAL DEFAULT "K",
  humidity_value INTEGER NOT NULL,
  humidity_unit TEXT DEFAULT "%",
  pressure_value INTEGER NOT NULL,
  pressure_unit TEXT DEFAULT "hPa", --default hPa
  wind_speed_value REAL NOT NULL,
  wind_speed_unit TEXT DEFAULT "meter/sec", --default meter/sec
  wind_speed_name TEXT NOT NULL, --
  wind_direction_value INTEGER NOT NULL,
  wind_direction_code INTEGER NOT NULL,
  wind_direction_name TEXT NOT NULL,
  clouds_value REAL NOT NULL,
  clouds_name TEXT NOT NULL,
  visibility_value INTEGER NOT NULL,
  precipitation_value INTEGER NOT NULL,
  precipitation_mode TEXT DEFAULT "%", -- default "%"
  weather_number INTEGER NOT NULL,
  weather_value INTEGER NOT NULL,
  weather_icon TEXT NOT NULL,
  lastupdate_value TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES owm_cities (city_id)
);

CREATE TABLE owm_hourly_weather_forecast (
  request_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  forecast_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
  city_id INTEGER NOT NULL,
  city_sun_rise INTEGER NOT NULL,
  city_sun_set INTEGER NOT NULL,
  timezone TEXT NOT NULL,
  temperature_value REAL NOT NULL,
  temperature_min REAL NOT NULL,
  temperature_max REAL NOT NULL,
  temperature_unit TEXT DEFAULT "K", --default Kelvin
  feels_like_value REAL NOT NULL,
  feels_like_unit REAL NOT NULL,
  humidity_value INTEGER NOT NULL,
  humidity_unit TEXT NOT NULL,
  pressure_value INTEGER NOT NULL,
  pressure_unit TEXT DEFAULT "hPa", --default hPa
  wind_speed_value REAL NOT NULL,
  wind_speed_unit TEXT DEFAULT "meter/sec", --default meter/sec
  wind_speed_name TEXT NOT NULL, --
  wind_direction_value INTEGER NOT NULL,
  wind_direction_code INTEGER NOT NULL,
  wind_direction_name TEXT NOT NULL,
  clouds_value REAL NOT NULL,
  clouds_name TEXT NOT NULL,
  visibility_value INTEGER NOT NULL,
  precipitation_value INTEGER NOT NULL,
  precipitation_mode TEXT DEFAULT "%", -- default "%"
  weather_number INTEGER NOT NULL,
  weather_value INTEGER NOT NULL,
  weather_icon TEXT NOT NULL,
  lastupdate_value TEXT NOT NULL,
  FOREIGN KEY (city_id) REFERENCES owm_cities (city_id)
);