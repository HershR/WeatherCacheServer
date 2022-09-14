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


def update_current_weather(city_id):
    db = get_db()
    city = db.execute(
        'SELECT * FROM owm_cities'
        ' WHERE city_id = ?',
        (city_id,)
    ).fetchone()
    error = None
    if city is None:
        error = 'city not currently tracked'
    else:
        latitude = city['city_coord_lat']
        longitude = city['city_coord_long']
        dt = datetime.datetime.now(timezone.utc)
        timestamp = int(dt.timestamp())
        timestamp = int(timestamp//360 * 360)  # floor to hour

        #print('dt: '+ str(dt))
        #print('timestamp: ' + str(timestamp) + ' -> '+ str(timestamp+360))

        # check if city's current weather has
        # already been updated this hour
        updated = db.execute(
            'SELECT timestamp FROM owm_current_weather'
            ' WHERE city_id = ? AND timestamp BETWEEN ? AND ?',
            (city_id, timestamp, (timestamp+360),)
        ).fetchone()
        if updated is not None:
            error = 'city has already been updated for current hour'
        else:
            url = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}".format(lat=latitude, lon=longitude, key=os.environ.get("OPENWEATHER_API_KEY"))
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()

                # some data is unavailable in api call, ex wind_speed name, clouds
                # will update incorrect fields at later time
                #pprint(data)
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
                    (city_id, data['sys']['sunrise'], data['sys']['sunset'], data['timezone'], data['dt'],
                     data['main']['temp'], data['main']['temp_min'], data['main']['temp_max'], data['main']['feels_like'],
                     data['main']['humidity'], data['main']['pressure'],
                     data['wind']['speed'], data['wind']['speed'], data['wind']['deg'], data['wind']['deg'], data['wind']['deg'],
                     data['clouds']['all'], data['clouds']['all'], data['visibility'], data['cod'],
                     data['id'], data['id'], data['id']
                     )
                )
                db.commit()
    return error


#get 5 days with hourly data
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
                    lat=latitude, lon=longitude, time=hour, key=os.environ.get("OPENWEATHER_API_KEY"))
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
                         data['current']['clouds'], data['current']['clouds'], data['current']['visibility'],
                         data['cod'],
                         data['current']['weather'][0]['id'], data['current']['weather'][0]['id'],
                         data['current']['weather'][0]['icon']
                         )
                    )
                    db.commit()
                    hour -= 360
                    continue
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
                    lat=latitude, lon=longitude, time=hour, key=os.environ.get("OPENWEATHER_API_KEY"))
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
                         data['current']['clouds'], data['current']['clouds'], data['current']['visibility'],
                         data['cod'],
                         data['current']['weather'][0]['id'], data['current']['weather'][0]['id'],
                         data['current']['weather'][0]['icon']
                         )
                    )
                    db.commit()
                    hour -= 360
                else:
                    error = 'error connecting to clean weather api'
                    break
    return error


@bp.route('/weather/<int:id>/current', methods=('GET', 'POST'))
def current_weather(id):
    print(update_current_weather(id))
    #update_historical(id)
    #update_historical_3h_opt(id)
    db = get_db()

    data = db.execute(
        'SELECT *, datetime(timestamp, "unixepoch") timestamp_f, datetime(lastupdate_value, "unixepoch") lastupdate_value_f'
        ' FROM owm_cities c'
        ' JOIN owm_current_weather w ON c.city_id = w.city_id'
        ' ORDER BY lastupdate_value DESC'
    ).fetchall()
    return render_template('weather/currentweather.html', data=data)


@bp.route('/weather/<int:id>/current/dump', methods=('GET', 'POST'))
def current_weather_dump(id):
    db = get_db()
    data = db.execute(
        'SELECT *'
        ' FROM owm_cities c'
        ' JOIN owm_current_weather w ON c.city_id = w.city_id'
        ' ORDER BY timestamp DESC'
    ).fetchall()

    return json.dumps( [dict(weather) for weather in data])  # CREATE JSON
