
# not tested nor updated to work with schema

import os
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

    url = 'https://pro.openweathermap.org/data/2.5/forecast/hourly?lat={lat}&lon={lon}&units=metric&cnt={count}&appid={API key}'.format(lat=latitude, lon=longitude, count=(24 * days), key=owm_api_key)
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
                url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&units=metric&dt={time}&appid={key}'.format(
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
                url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&units=metric&dt={time}&appid={key}'.format(
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

