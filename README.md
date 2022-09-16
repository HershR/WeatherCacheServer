# WeatherCacheApp
 Flask server that tracks and stores the weather forecast of cities specified cities.
  
 Makes use of [Open Weather Map API](https://openweathermap.org/)
 **(Note: Some functions require paid API key)**
 
## Current features
- Get and store hourly forecast
- Get and store forecast for the next 2 days in 3h intervals
- Get and store historical weather data up to five days into the past in 1h intervals **(not tested)**
 
## Set Key
- Create an environment variable called OPENWEATHERMAP_API_KEY and set it to your key
or
- Replace owm_api_key variable in weather.py with desired key
## How to Run Locally
```
$ set FLASK_APP=flaskr 
$ set FLASK_ENV=development 
$ set FLASK_DEBUG=1
$ flask init-db
$ flask run
```

Required Packages in requirements.txt
