# Hersh Rudrawal
# weather.py
# Contains functions required to update
# the database with weather data
# Also contains the page routes to display
# the data in db
# note: not all inserted field contains correct values,

import os
import xmltodict
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
owm_api_key = os.environ.get("OPENWEATHERMAP_API_KEY")


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
        # get weather data in xml format
        url = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric&mode=xml".format(lat=latitude, lon=longitude, key=owm_api_key)
        r = requests.get(url)
        if r.status_code == 200:
            #convert to dictionary
            data = xmltodict.parse(r.content, attr_prefix="")
            # insert data into owm_current_weather
            db.execute(
                "INSERT INTO owm_current_weather "
                "(city_id, city_sun_rise, city_sun_set, timezone_offset, lastupdate_value,"
                "temperature_value, temperature_min, temperature_max, temperature_unit,"
                "feels_like_value, feels_like_unit, humidity_value, pressure_value,"
                "wind_speed_value, wind_speed_name, wind_direction_value_deg, wind_direction_code, wind_direction_name,"
                "clouds_value_pct, clouds_name, visibility_value_m, precipitation_value_mm, precipitation_mode,"
                "weather_number, weather_value, weather_icon)"
                "VALUES (? , ? , ? , ? , ?,"
                "? , ? , ? , ? ,"
                "?, ?, ? , ? ,"
                "? , ? , ? , ? , ?,"
                "? , ?, ? , ? , ?,"
                "? , ? , ? )",
                (city_id, data['current']['city']['sun']['rise'], data['current']['city']['sun']['set'], data['current']['city']['timezone'], data['current']['lastupdate']['value'],
                 data['current']['temperature']['value'], data['current']['temperature']['min'], data['current']['temperature']['max'], data['current']['temperature']['unit'],
                 data['current']['feels_like']['value'], data['current']['feels_like']['unit'], data['current']['humidity']['value'], data['current']['pressure']['value'],
                 data['current']['wind']['speed']['value'], data['current']['wind']['speed']['name'], data['current']['wind']['direction']['value'], data['current']['wind']['direction']['code'], data['current']['wind']['direction']['name'],
                 data['current']['clouds']['value'], data['current']['clouds']['name'], data['current']['visibility']['value'], 0 if 'value' not in data['current']['precipitation'] else data['current']['precipitation']['value'], data['current']['precipitation']['mode'],
                 data['current']['weather']['number'], data['current']['weather']['value'], data['current']['weather']['icon'],
                 )
            )
            db.commit()

        else:
            error = 'failed to connect to Open Weather API\nstatus code: ' + str(r.status_code)
    return error


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
        url = 'http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&cnt={count}&appid={key}&mode=xml'.format(lat=latitude, lon=longitude, count=((8 * days)-1), key=owm_api_key)
        r = requests.get(url)
        if r.status_code == 200:
            # convert to dictionary
            data = xmltodict.parse(r.content, attr_prefix="")['weatherdata']
            for i in range(0, ((8 * days)-1)):
                exist = None
                exist = db.execute(
                    'SELECT c.city_id'
                    ' FROM owm_cities c'
                    ' JOIN owm_hourly_weather_forecast w ON c.city_id = w.city_id'
                    ' WHERE c.city_id = ? AND w.forecast_timestamp = ?',
                    (city_id, data['forecast']['time'][i]['from'])
                ).fetchone()
                if exist is not None:
                    continue
                db.execute(
                    "INSERT INTO owm_hourly_weather_forecast "
                    "(forecast_timestamp, lastupdate_value,"
                    "city_id, city_sun_rise, city_sun_set, timezone_offset,"
                    "temperature_value, temperature_min, temperature_max, temperature_unit,"
                    "feels_like_value, feels_like_unit, humidity_value, pressure_value,"
                    "wind_speed_value, wind_speed_name, wind_direction_value_deg, wind_direction_code, wind_direction_name,"
                    "clouds_value_pct, clouds_name, visibility_value_m, precipitation_value_mm, precipitation_mode,"
                    "weather_number, weather_value, weather_icon)"
                    "VALUES (? , ?,"
                    "? , ? , ? , ? ,"
                    "? , ? , ? , ? ,"
                    "?, ?, ? , ? ,"
                    "? , ? , ? , ? , ?,"
                    "? , ?, ? , ? , ?,"
                    "? , ? , ? )",
                    (data['forecast']['time'][i]['from'], data['meta']['lastupdate'],
                     city_id, data['sun']['rise'], data['sun']['set'], data['location']['timezone'],
                     data['forecast']['time'][i]['temperature']['value'], data['forecast']['time'][i]['temperature']['min'], data['forecast']['time'][i]['temperature']['max'], data['forecast']['time'][i]['temperature']['unit'],
                     data['forecast']['time'][i]['feels_like']['value'], data['forecast']['time'][i]['feels_like']['unit'], data['forecast']['time'][i]['humidity']['value'], data['forecast']['time'][i]['pressure']['value'],
                     data['forecast']['time'][i]['windSpeed']['mps'], data['forecast']['time'][i]['windSpeed']['name'], data['forecast']['time'][i]['windDirection']['deg'], data['forecast']['time'][i]['windDirection']['code'], data['forecast']['time'][i]['windDirection']['name'],
                     data['forecast']['time'][i]['clouds']['all'], data['forecast']['time'][i]['clouds']['value'], data['forecast']['time'][i]['visibility']['value'], 0 if 'value' not in data['forecast']['time'][i]['precipitation'] else data['forecast']['time'][i]['precipitation']['value'], data['forecast']['time'][i]['precipitation']['type'],
                     data['forecast']['time'][i]['symbol']['number'], data['forecast']['time'][i]['symbol']['name'], data['forecast']['time'][i]['symbol']['var'],
                     )
                )
            db.commit()
        else:
            error = 'failed to connect to Open Weather API'
    return error

#Routes

# updates the current weather to owm_current_weather for given city
@bp.route('/weather/<int:city_id>/current', methods=('GET', 'POST'))
def current_weather(city_id):
    error = None
    error = update_current_weather(city_id)
    if error is None:
        db = get_db()
        data = db.execute(
            'SELECT *, datetime(timestamp, "unixepoch") timestamp_f, datetime(lastupdate_value, "unixepoch") lastupdate_value_f'
            ' FROM owm_cities c'
            ' JOIN owm_current_weather w ON c.city_id = w.city_id'
            ' ORDER BY lastupdate_value DESC'
        ).fetchall()
        return render_template('weather/currentweather.html', data=data)
    else:
        flash(error)
        return redirect(url_for('cityTable.index'))


# updates the current forcast to owm_hourly_weather_forecast for given city
@bp.route('/weather/<int:city_id>/forecast', methods=('GET', 'POST'))
def current_forecast(city_id):
    error = None
    error = update_forcast_3h(city_id)
    if error is None:
        db = get_db()
        data = db.execute(
            'SELECT *, datetime(forecast_timestamp, "unixepoch") forecast_timestamp_f,'
            ' datetime(lastupdate_value, "unixepoch") lastupdate_value_f,'
            ' datetime(request_timestamp, "unixepoch") request_timestamp_f'
            ' FROM owm_cities c'
            ' JOIN owm_hourly_weather_forecast w ON c.city_id = w.city_id'
            ' WHERE c.city_id = ?'
            ' ORDER BY forecast_timestamp ASC', (city_id,)
        ).fetchall()
        return render_template('weather/currentforecast.html', data=data)
    else:
        flash(error)
        return redirect(url_for('cityTable.index'))




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
