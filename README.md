# WeatherCacheApp
 Flask server that tracks and stores the weather forecast of cities specified cities.
  
 Makes use of [Open Weather Map API](https://openweathermap.org/api)
 **(Note: Some functions require paid API key)**
 
## Current features
- Get and store current forecast
- Get and store forecast for the next day in 3h intervals


## Set Open Weather Maps API Key
- Create an environment variable called OPENWEATHERMAP_API_KEY and set it to your key
```
$ set OPENWEATHERMAP_API_KEY="key"
```
or
- Replace owm_api_key variable in weather.py and cities.py with desired key

## Set Database URL
- Create an environment variable called DATABASE_URL and set it to your database url/location
- ex postgres
```
$ set DATABASE_URL=postgres://"username":"password""host"/"databasename"
```

## Create Database/Tables
Run the following script in python
```
from flaskr import db, create_app
from flaskr.models import *

db.create_all(app=create_app())
```
## Run Locally
```
$ set FLASK_APP=flaskr
$ set FLASK_ENV=development
$ set FLASK_DEBUG=1
$ flask run
```

## Update Database Tables
```
$ flask db.migrate
$ flask db.upgrade
```


Required Packages in requirements.txt
