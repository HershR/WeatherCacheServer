# Hersh Rudrawal
# weather.py
# Contains functions required to update
# the database with weather data
# Also contains the page routes to display
# the data in db
# note: not all inserted field contains correct values,

import os
import json
import requests
import datetime

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from datetime import timezone

from pprint import pprint
from pyowm.owm import OWM

from werkzeug.exceptions import abort

from flaskr.db import get_db

bp = Blueprint('weather', __name__)

# Add your own Open Weather Api Key here
owm_api_key = os.environ.get("OPENWEATHER_API_KEY")


# Returns the name of a given wind speed mph
def wind_name(speed):
    if 0 < speed < 1:
        return 'Calm'
    elif 1 <= speed < 4:
        return 'Light Air'
    elif 4 <= speed < 8:
        return 'Light Breeze'
    elif 8 <= speed < 13:
        return 'Gentle Breeze'
    elif 13 <= speed < 19:
        return 'Moderate Breeze'
    elif 19 <= speed < 25:
        return 'Fresh Breeze'
    elif 25 <= speed < 32:
        return 'Strong Breeze'
    elif 32 <= speed < 39:
        return 'Near Gale'
    elif 39 <= speed < 47:
        return 'Gale'
    elif 47 <= speed < 55:
        return 'Severe Gale'
    elif 55 <= speed < 64:
        return 'Storm'
    elif 64 <= speed < 73:
        return 'Violent Storm'
    elif speed >= 73:
        return 'Hurricane'
    else:
        return 'weather Error: calling wind_name() with negative speed value'


# converts degrees to  cardinal direction name or code
# for code set second parameter to True
# from: https://stackoverflow.com/questions/7490660/converting-wind-direction-in-angles-to-text-words
cardinal_direction_codes = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
cardinal_direction = ["North", "North-NorthEast", "NorthEast", "East-NorthEast", "East", "East-SouthEast", "SouthEast", "South-SouthEast",
                      "South", "South-SouthWest", "SouthWest", "West-SouthWest", "West", "West-NorthWest", "NorthWest", "North-NorthWest"]
def wind_direction_name(degree, code = False):
    # ensure degree is between 0 and 360
    if degree > 360 or degree < 0:
        degree = degree % 360

    index = int((degree/22.5)+.5)
    if code:
        return cardinal_direction_codes[index % 16]
    else:
        return cardinal_direction[index % 16]


# will get the current weather for a given city
# and updated owm_current_weather with the data
# able to call with free api key
def update_current_weather(city_id):
    error = None
    latitude = None
    longitude = None
    db = get_db()
    # check is city is being tracked
    city = db.execute(
        'SELECT * FROM owm_cities'
        ' WHERE city_id = ?',
        (city_id,)
    ).fetchone()
    if city is None:
        error = 'city not currently tracked'
    else:
        latitude = city['city_coord_lat']
        longitude = city['city_coord_long']
        if latitude is None or longitude is None:
            error = 'coordinates missing for city: ' + str(city_id)

    if error is None:
        # get weather data
        url = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}".format(lat=latitude, lon=longitude, key=owm_api_key)
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()

            # insert data into owm_current_weather
            # some data is unavailable in api call, ex clouds name
            # will update incorrect fields at later time
            db.execute(
                "INSERT INTO owm_current_weather "
                "(city_id, city_sun_rise, city_sun_set, timezone, lastupdate_value,"
                "temperature_value, temperature_min, temperature_max, feels_like_value,"
                "humidity_value, pressure_value,"
                "wind_speed_value, wind_speed_name, wind_direction_value, wind_direction_code, wind_direction_name,"
                "clouds_value, clouds_name, visibility_value, precipitation_value,"
                "weather_number, weather_value, weather_icon)"
                "VALUES (? , ? , ? , ? , ?,"
                "? , ? , ? , ? ,"
                "? , ? ,"
                "? , ? , ? , ? , ?,"
                "? , ? , ? , ? ,"
                "? , ? , ? )",
                (city_id, data['sys']['sunrise'], data['sys']['sunset'], data['timezone'], data['dt'],
                 data['main']['temp'], data['main']['temp_min'], data['main']['temp_max'], data['main']['feels_like'],
                 data['main']['humidity'], data['main']['pressure'],
                 data['wind']['speed'], wind_name(data['wind']['speed']), data['wind']['deg'], wind_direction_name(data['wind']['deg'], True), wind_direction_name(data['wind']['deg']),
                 data['clouds']['all'], data['clouds']['all'], data['visibility'], data['cod'],
                 data['weather'][0]['id'], data['weather'][0]['main'], data['weather'][0]['icon']
                 )
            )
            db.commit()
        else:
            error = 'failed to connect to Open Weather API\nstatus code: ' + str(r.status_code)
    return error


# will get the forcast for the next x days, max 5, in 3h intervals
# (starts at the next day at 03:00:00 UTC)
# then updates owm_hourly_weather_forecast with data
# by default only gets tomorrow's forecast
# works with free api key
def update_forcast_3h(city_id, days=1):
    error = None
    # ensure days is within range
    if days < 1:
        days = 1
    if days > 5:
        days = 5
    db = get_db()
    # check is city is being tracked
    coords = db.execute(
        'SELECT city_coord_long, city_coord_lat'
        ' FROM owm_cities'
        ' WHERE city_id = ?',
        (city_id,)
    ).fetchone()
    latitude = None
    longitude = None
    if coords is None:
        error = ('not tracking city with id: ' + str(city_id))
    else:
        latitude = coords['city_coord_lat']
        longitude = coords['city_coord_long']
        if latitude is None or longitude is None:
            error = 'coordinates missing for city: ' + str(city_id)

    if error is None:
        url = 'http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&cnt={count}&appid={key}'.format(lat=latitude, lon=longitude, count=((8 * days)-1), key=owm_api_key)
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            for i in range(0, data['cnt']):
                cur = db.cursor()
                # first attempt updating the table for the given forecast_timestamp
                cur.execute(
                    "UPDATE owm_hourly_weather_forecast"
                    " SET request_timestamp = ?, lastupdate_value = ?,"
                    "temperature_value = ?, temperature_min = ?, temperature_max = ?, feels_like_value = ?,"
                    "humidity_value = ?, pressure_value = ?,"
                    "wind_speed_value = ?, wind_speed_name = ?, wind_direction_value = ?, wind_direction_code = ?, wind_direction_name = ?,"
                    "clouds_value = ?, clouds_name = ?, visibility_value = ?, precipitation_value = ?,"
                    "weather_number = ?, weather_value = ?, weather_icon = ?"
                    " WHERE city_id = ? AND forecast_timestamp = ? ",
                    (int(datetime.datetime.now(timezone.utc).timestamp()), data['list'][i]['dt'],
                     data['list'][i]['main']['temp'], data['list'][i]['main']['temp_min'], data['list'][i]['main']['temp_max'], data['list'][i]['main']['feels_like'],
                     data['list'][i]['main']['humidity'], data['list'][i]['main']['pressure'],
                     data['list'][i]['wind']['speed'], wind_name(data['list'][i]['wind']['speed']), data['list'][i]['wind']['deg'], wind_direction_name(data['list'][i]['wind']['deg'], True), wind_direction_name(data['list'][i]['wind']['deg']),
                     data['list'][i]['clouds']['all'], data['list'][i]['clouds']['all'], data['list'][i]['visibility'], data['list'][i]['pop'],
                     data['list'][i]['weather'][0]['id'], data['list'][i]['weather'][0]['main'], data['list'][i]['weather'][0]['icon'],
                     city_id, data['list'][i]['dt'],
                     )
                )
                # c equals the number of rows updated in the previous execute call
                c = cur.rowcount
                if c == 0:
                    # no rows updated, then insert
                    db.execute(
                        "INSERT INTO owm_hourly_weather_forecast"
                        "(forecast_timestamp, lastupdate_value,"
                        "city_id, city_sun_rise, city_sun_set, timezone, "
                        "temperature_value, temperature_min, temperature_max, feels_like_value,"
                        "humidity_value, pressure_value,"
                        "wind_speed_value, wind_speed_name, wind_direction_value, wind_direction_code, wind_direction_name,"
                        "clouds_value, clouds_name, visibility_value, precipitation_value,"
                        "weather_number, weather_value, weather_icon)"
                        " VALUES (?, ?,"
                        "? , ? , ? , ? ,"
                        "? , ? , ? , ? ,"
                        "? , ? ,"
                        "? , ? , ? , ? , ?,"
                        "? , ? , ? , ? ,"
                        "? , ? , ?)",
                        (data['list'][i]['dt'], data['list'][i]['dt'],
                         city_id, data['city']['sunrise'], data['city']['sunset'], data['city']['timezone'],
                         data['list'][i]['main']['temp'], data['list'][i]['main']['temp_min'], data['list'][i]['main']['temp_max'], data['list'][i]['main']['feels_like'],
                         data['list'][i]['main']['humidity'], data['list'][i]['main']['pressure'],
                         data['list'][i]['wind']['speed'], wind_name(data['list'][i]['wind']['speed']), data['list'][i]['wind']['deg'], wind_direction_name(data['list'][i]['wind']['deg'], True), wind_direction_name(data['list'][i]['wind']['deg']),
                         data['list'][i]['clouds']['all'], data['list'][i]['clouds']['all'], data['list'][i]['visibility'], data['list'][i]['pop'],
                         data['list'][i]['weather'][0]['id'], data['list'][i]['weather'][0]['main'], data['list'][i]['weather'][0]['icon']
                         )
                    )
                elif c > 1:
                    # multiple rows where updated, duplicated rows exist
                    error = 'duplicate rows found'
                    return error
            db.commit()
        else:
            error = 'failed to connect to Open Weather API'
    return error


# will get the forcast for the next x days, max 4, in 1h intervals
# then updates owm_hourly_weather_forecast with data
# by default only gets tomorrow's forecast
# note: not tested, requires paid API key
def update_forecast(city_id, days=1):
    error = None
    if days < 1:
        days = 1
    if days > 4:
        days = 4
    db = get_db()
    coords = db.execute(
        'SELECT city_coord_long, city_coord_lat'
        ' FROM owm_cities'
        ' WHERE city_id = ?',
        (city_id,)
    ).fetchone()
    latitude = None
    longitude = None
    if coords is None:
        error = ('not tracking city with id: ' + str(city_id))
    else:
        latitude = coords['city_coord_lat']
        longitude = coords['city_coord_long']

    if latitude is None or longitude is None:
        error = 'coordinated missing for city: ' + str(city_id)

    url = 'https://pro.openweathermap.org/data/2.5/forecast/hourly?lat={lat}&lon={lon}&cnt={count}&appid={API key}'.format(lat=latitude, lon=longitude, count=(24 * days), key=owm_api_key)
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        for i in range(data['cnt']):
            db.execute(
                "INSERT INTO owm_hourly_weather_forecast"
                "(forecast_timestamp, lastupdate_value,"
                "city_id, city_sun_rise, city_sun_set, timezone, "
                "temperature_value, temperature_min, temperature_max, feels_like_value,"
                "humidity_value, pressure_value,"
                "wind_speed_value, wind_speed_name, wind_direction_value, wind_direction_code, wind_direction_name,"
                "clouds_value, clouds_name, visibility_value, precipitation_value,"
                "weather_number, weather_value, weather_icon)"
                " VALUES (?, ?,"
                "? , ? , ? , ? ,"
                "? , ? , ? , ? ,"
                "? , ? ,"
                "? , ? , ? , ? , ?,"
                "? , ? , ? , ? ,"
                "? , ? , ?)",
                (data['list'][i]['dt'], data['list'][i]['dt'],
                 city_id, data['city']['sunrise'], data['city']['sunset'], data['city']['timezone'],
                 data['list'][i]['main']['temp'], data['list'][i]['main']['temp_min'], data['list'][i]['main']['temp_max'],
                 data['list'][i]['main']['feels_like'],
                 data['list'][i]['main']['humidity'], data['list'][i]['main']['pressure'],
                 data['list'][i]['wind']['speed'], wind_name(data['list'][i]['wind']['speed']), data['list'][i]['wind']['deg'],
                 wind_direction_name(data['list'][i]['wind']['deg'], True), wind_direction_name(data['list'][i]['wind']['deg']),
                 data['list'][i]['clouds']['all'], data['list'][i]['clouds']['all'], data['list'][i]['visibility'],
                 data['list'][i]['pop'],
                 data['list'][i]['weather'][0]['id'], data['list'][i]['weather'][0]['main'],
                 data['list'][i]['weather'][0]['icon']
             )
    )
    return error


# will get check owm_current_weather table for missing data
# and updated the table with historical hourly weather data
# up to five days prior#
# note: not tested, requires paid API key
def update_history(city_id):
    error = None
    db = get_db()
    coords = db.execute(
        'SELECT city_coord_long, city_coord_lat'
        ' FROM owm_cities'
        ' WHERE city_id = ?',
        (city_id,)
    ).fetchone()
    latitude = None
    longitude = None
    if coords is None:
        error = ('not tracking city with id: ' + str(city_id))
    else:
        latitude = coords['city_coord_lat']
        longitude = coords['city_coord_long']

    if latitude is None or longitude is None:
        error = 'coordinated missing for city: ' + str(city_id)

    timestamps = db.execute(
        ' SELECT lastupdate_value FROM owm_current_weather'
        ' WHERE city_id = ?'
        ' ORDER BY lastupdate_value DESC',
        (city_id,)
    ).fetchall()

    if timestamps is not None:
        # iterate through current data to fill missing data

        # get current utc timestamp and floor it to last hour
        utctime = int(datetime.datetime.now(timezone.utc).timestamp())
        utchourlytime = int(utctime // 360 * 360)
        hour = utchourlytime

        t = 0  # timestamps index
        while hour > utchourlytime - (5 * 24 * 360):
            # loop up to 5 days into past, max 120 loops
            if t >= len(timestamps):
                # no more db timestamps to check, fill db with remaining hours
                url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={time}&appid={key}'.format(
                    lat=latitude, lon=longitude, time=hour, key=owm_api_key)
                r = requests.get(url)
                if r.status_code == 200:
                    data = r.json()
                    db.execute(
                        "INSERT INTO owm_current_weather "
                        "(city_id, city_sun_rise, city_sun_set, timezone, lastupdate_value,"
                        "temperature_value, temperature_min, temperature_max, feels_like_value,"
                        "humidity_value, pressure_value,"
                        "wind_speed_value, wind_speed_name, wind_direction_value, wind_direction_code, wind_direction_name,"
                        "clouds_value, clouds_name, visibility_value, precipitation_value,"
                        "weather_number, weather_value, weather_icon)"
                        "VALUES (? , ? , ? , ? , ?,"
                        "? , ? , ? , ? ,"
                        "? , ? ,"
                        "? , ? , ? , ? , ?,"
                        "? , ? , ? , ? ,"
                        "? , ? , ?)",
                        (city_id, data['current']['sunrise'], data['current']['sunset'], data['timezone'],
                         data['current']['dt'],
                         data['current']['temp'], data['current']['temp_min'], data['current']['temp_max'],
                         data['current']['feels_like'],
                         data['current']['humidity'], data['current']['pressure'],
                         data['current']['wind_speed'], data['current']['wind_speed'], data['current']['wind_deg'],
                         data['current']['wind_deg'],
                         data['current']['wind_deg'],
                         data['current']['clouds'], data['current']['clouds'], data['current']['visibility'], data['hourly']['pop'],
                         data['current']['weather'][0]['id'], data['current']['weather'][0]['main'], data['current']['weather'][0]['icon'],
                         )
                    )
                    db.commit()
                    hour -= 360
                    continue
                else:
                    error = 'failed to connect to Open Weather API'

            dbtimestamp = timestamps[t]['lastupdate_value']
            if dbtimestamp in range(hour, hour + 360):
                hour -= 360
                t += 1
                continue

            if dbtimestamp > hour + 360:
                # duplicate entries for 1 or more timestamps
                db.execute('DELETE FROM owm_current_weather WHERE timestamp = ?',
                           (dbtimestamp,)
                           )
                db.commit()
                t += 1
            if dbtimestamp < hour:
                #missing data
                url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={time}&appid={key}'.format(
                    lat=latitude, lon=longitude, time=hour, key=owm_api_key)
                r = requests.get(url)
                if r.status_code == 200:
                    data = r.json()
                    db.execute(
                        "INSERT INTO owm_current_weather "
                        "(city_id, city_sun_rise, city_sun_set, timezone, lastupdate_value,"
                        "temperature_value, temperature_min, temperature_max, feels_like_value,"
                        "humidity_value, pressure_value,"
                        "wind_speed_value, wind_speed_name, wind_direction_value, wind_direction_code, wind_direction_name,"
                        "clouds_value, clouds_name, visibility_value, precipitation_value,"
                        "weather_number, weather_value, weather_icon)"
                        "VALUES (? , ? , ? , ? , ?,"
                        "? , ? , ? , ? ,"
                        "? , ? ,"
                        "? , ? , ? , ? , ?,"
                        "? , ? , ? , ? ,"
                        "? , ? , ?)",
                        (city_id, data['current']['sunrise'], data['current']['sunset'], data['timezone'], data['current']['dt'],
                         data['current']['temp'], data['current']['temp_min'], data['current']['temp_max'], data['current']['feels_like'],
                         data['current']['humidity'], data['current']['pressure'],
                         data['current']['wind_speed'], wind_name(data['current']['wind_speed']), data['current']['wind_deg'], wind_direction_name(data['current']['wind_deg'], True), wind_direction_name(data['current']['wind_deg']),
                         data['current']['clouds'], data['current']['clouds'], data['current']['visibility'], data['hourly']['pop'],
                         data['current']['weather'][0]['id'], data['current']['weather'][0]['id'], data['current']['weather'][0]['icon']
                         )
                    )
                    db.commit()
                    hour -= 360
                else:
                    error = 'failed to connect to Open Weather API'
                    break
    return error


#Routes

# updates the current weather to owm_current_weather for given city
@bp.route('/weather/<int:city_id>/current', methods=('GET', 'POST'))
def current_weather(city_id):
    error = None
    error = update_current_weather(city_id)
    db = get_db()
    data = db.execute(
        'SELECT *, datetime(timestamp, "unixepoch") timestamp_f, datetime(lastupdate_value, "unixepoch") lastupdate_value_f'
        ' FROM owm_cities c'
        ' JOIN owm_current_weather w ON c.city_id = w.city_id'
        ' ORDER BY lastupdate_value DESC'
    ).fetchall()

    return render_template('weather/currentweather.html', data=data)


# updates the current forcast to owm_hourly_weather_forecast for given city
@bp.route('/weather/<int:city_id>/forecast', methods=('GET', 'POST'))
def current_forecast(city_id):
    print(update_forcast_3h(city_id))
    db = get_db()
    data = db.execute(
        'SELECT *, datetime(forecast_timestamp, "unixepoch") forecast_timestamp_f,'
        'datetime(lastupdate_value, "unixepoch") lastupdate_value_f,'
        'datetime(request_timestamp, "unixepoch") request_timestamp_f'
        ' FROM owm_cities c'
        ' JOIN owm_hourly_weather_forecast w ON c.city_id = w.city_id'
        ' WHERE c.city_id = ?'
        ' ORDER BY forecast_timestamp ASC', (city_id,)
    ).fetchall()
    return render_template('weather/currentforecast.html', data=data)

# returns all data in owm_current_weather for a given city as a json
@bp.route('/weather/<int:city_id>/current/dump', methods=('GET', 'POST'))
def current_weather_dump(city_id):
    db = get_db()
    data = db.execute(
        'SELECT *'
        ' FROM owm_cities c'        
        ' JOIN owm_current_weather w ON c.city_id = w.city_id'  
        ' WHERE c.city_id = ?'
        ' ORDER BY timestamp DESC', (city_id,)
    ).fetchall()

    return json.dumps([dict(weather) for weather in data])  # CREATE JSON

# returns all data in owm_hourly_weather_forecast for a given city as a json
@bp.route('/weather/<int:city_id>/forecast/dump', methods=('GET', 'POST'))
def forecast_dump(city_id):
    db = get_db()
    data = db.execute(
        'SELECT *'
        ' FROM owm_cities c'        
        ' JOIN owm_hourly_weather_forecast w ON c.city_id = w.city_id'  
        ' WHERE c.city_id = ?'
        ' ORDER BY forecast_timestamp ASC', (city_id,)
    ).fetchall()

    return json.dumps([dict(weather) for weather in data])  # CREATE JSON
