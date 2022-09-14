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
        timestamp = timestamp//360 * 360  # floor to hour

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
            url = "https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}" \
                .format(lat=latitude, lon=longitude,
                        key=os.environ.get("OPENWEATHER_API_KEY"))
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

'''
# will update the past 5 days, at 3 hour intervals, use if free api key
# initial ver of function, not fix or optimized
def update_historical_3h(city_id):
    db = get_db()
    error = None
    coords = db.execute(
        'SELECT city_coord_long, city_coord_lat'
        ' FROM owm_cities'
        ' WHERE city_id = ?',
        (city_id,)
    ).fetchone()
    if coords is None:
        error = 'fail to get coords'
        return error
    latitude = coords['city_coord_lat']
    longitude = coords['city_coord_long']
    data = db.execute(
        ' SELECT timestamp FROM owm_current_weather'
        ' WHERE city_id = ?'
        ' ORDER BY timestamp DESC',
        (city_id,)
    ).fetchall()

    if data is not None:
        # floor the most recent timestamp by the hour
        # iterate through the timestamps and check if there are missing hours
        # fill in missing hours
        utctime = int(datetime.datetime.now(timezone.utc).timestamp())
        floorts = int(utctime // 360 * 360)  # floored utc time stamp to last hour

        ''''''testing
        ts = datetime.datetime.utcfromtimestamp(utctime)
        print(str(utctime) + " -> " + str(ts.strftime('%H:%M:%S')))                
        floorts = datetime.datetime.utcfromtimestamp(floorts)
        print(str(floorts) + " -> " + str(floorts.strftime('%H:%M:%S')))
        ''''''
        
        fts = floorts
        url = 'https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}'.format(lat=latitude, lon=longitude, key=os.environ.get("OPENWEATHER_API_KEY"))
        r = requests.get(url)
        for d in data:
            timestamp = d['timestamp']
            if fts < floorts - (5 * 24 * 60 * 60):
                # check if we have gone past 5 day mark
                break
            if timestamp in range(fts, fts + 3*360):
                fts -= 3 * 360
                continue
            else:
                #missing data
                if timestamp < fts:                    
                    if(r.status_code == 200):
                        weather = r.json()
                        for i in range(0, weather['cnt']):
                            if timestamp > fts:
                                break
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
                                (city_id, weather['city']['sunrise'], weather['city']['sunset'], weather['city']['timezone'], weather['list'][i]['dt'],
                                 weather['list'][i]['main']['temp'], weather['list'][i]['main']['temp_min'], weather['list'][i]['main']['temp_max'], weather['list'][i]['main']['feels_like'],
                                 weather['list'][i]['main']['humidity'], weather['list'][i]['main']['pressure'],
                                 weather['list'][i]['wind']['speed'], weather['list'][i]['wind']['speed'], weather['list'][i]['wind']['deg'], weather['list'][i]['wind']['deg'], weather['list'][i]['wind']['deg'],
                                 weather['list'][i]['clouds']['all'], weather['list'][i]['clouds']['all'], weather['list'][i]['visibility'], 5,
                                 weather['list'][i]['weather'][0]['id'], weather['list'][i]['weather'][0]['id'], weather['list'][i]['weather'][0]['id'],
                                 )
                            )
                            db.commit()
                            fts -= 360
                    else:
                        error = 'failed request to open api'
    return error

# will get next 5 day forcast, at 3 hour intervals, use if free api key

# need to check for optimization
def update_historical_3h_opt(city_id):
    db = get_db()
    error = None
    coords = db.execute(
        'SELECT city_coord_long, city_coord_lat'
        ' FROM owm_cities'
        ' WHERE city_id = ?',
        (city_id,)
    ).fetchone()
    if coords is None:
        error = 'fail to get coords'
        return error
    latitude = coords['city_coord_lat']
    longitude = coords['city_coord_long']
    hours = db.execute(
        ' SELECT city_id , lastupdate_value FROM owm_current_weather'
        ' WHERE city_id = ?'
        ' ORDER BY lastupdate_value DESC',
        (city_id,)
    ).fetchall()

    if hours is not None:
        url='https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={key}'.format(lat=latitude, lon=longitude, key=os.environ.get("OPENWEATHER_API_KEY"))
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            # range should be from 0 to 40, 5 days split into 3 hour intervals = 40
            h = 0 # hours index
            for i in range(0, data['cnt']):
                tracker = 0

                if h >= len(hours):
                    # filled missing up until last timestamp in db
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
                        (city_id, data['city']['sunrise'], data['city']['sunset'], data['city']['timezone'],
                         data['list'][i]['dt'],
                         data['list'][i]['main']['temp'], data['list'][i]['main']['temp_min'],
                         data['list'][i]['main']['temp_max'], data['list'][i]['main']['feels_like'],
                         data['list'][i]['main']['humidity'], data['list'][i]['main']['pressure'],
                         data['list'][i]['wind']['speed'], data['list'][i]['wind']['speed'],
                         data['list'][i]['wind']['deg'], data['list'][i]['wind']['deg'], data['list'][i]['wind']['deg'],
                         data['list'][i]['clouds']['all'], data['list'][i]['clouds']['all'],
                         data['list'][i]['visibility'], 5,
                         data['list'][i]['weather'][0]['id'], data['list'][i]['weather'][0]['id'],
                         data['list'][i]['weather'][0]['id'],
                         )
                    )
                    db.commit()
                    i += 1
                else:
                    # floor the most recent timestamp by the hour
                    # iterate through the timestamps and check if there are missing hours
                    # fill in missing hours
                    fts = int(data['list'][i]['dt']//360 * 360)
                    if hours[h]['lastupdate_value'] in range(fts, data['list'][i-1]['dt'] if i > 0 else fts + 3 * 360):
                        i += 1
                        continue

                    if hours[h]['lastupdate_value'] >= data['list'][i-1]['dt'] if i > 0 else fts + 3 * 360:
                        while hours[h]['lastupdate_value'] >= data['list'][i - 1]['dt'] if i > 0 else fts + 3 * 360:
                            if h>=len(hours):
                                break
                            db.execute('DELETE FROM owm_current_weather WHERE city_id = ? AND lastupdate_value = ?',
                                       (city_id, hours[h]['lastupdate_value'],))
                            db.commit()
                            h += 1
                    else:
                        while hours[h]['lastupdate_value'] < fts:
                            if i >= len(hours) or i >= data['cnt'] or h >= len(hours):
                                break
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
                                (city_id, data['city']['sunrise'], data['city']['sunset'], data['city']['timezone'],
                                 data['list'][i]['dt'],
                                 data['list'][i]['main']['temp'], data['list'][i]['main']['temp_min'],
                                 data['list'][i]['main']['temp_max'], data['list'][i]['main']['feels_like'],
                                 data['list'][i]['main']['humidity'], data['list'][i]['main']['pressure'],
                                 data['list'][i]['wind']['speed'], data['list'][i]['wind']['speed'],
                                 data['list'][i]['wind']['deg'], data['list'][i]['wind']['deg'], data['list'][i]['wind']['deg'],
                                 data['list'][i]['clouds']['all'], data['list'][i]['clouds']['all'],
                                 data['list'][i]['visibility'], 5,
                                 data['list'][i]['weather'][0]['id'], data['list'][i]['weather'][0]['id'],
                                 data['list'][i]['weather'][0]['id'],
                                 )
                            )
                            db.commit()
                            i += 1
                        h += 1
    return error
'''

#get 5 days with hourly data
def update_historical(city_id):
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
        #iterate through current data to fill missing data

        # floor the most recent timestamp by the hour
        # iterate through the timestamps and check if there are missing hours
        # fill in missing hours
        utctime = int(datetime.datetime.now(timezone.utc).timestamp())
        utchourlytime = int(utctime // 360 * 360)
        hour = utchourlytime

        
        for timestamp in timestamps:
            time = timestamp['timestamp']
            if hour < utchourlytime - (5*24*60*60):
                break
            if time in range(hour, hour + 360):
                hour -= 360
                continue
            else:
                #missing data
                if time < hour:
                    while hour > time:
                        if hour < 0 or time in range(hour, hour + 360) or hour < utchourlytime - (5*24*60*60):
                            break
                        # call historical weather data for timestamp
                        url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={time}&appid={key}'.format(lat=latitude, lon=longitude, time=hour, key=os.environ.get("OPENWEATHER_API_KEY"))
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
                                 data['current']['temp'], data['current']['temp_min'], data['current']['temp_max'],
                                 data['current']['feels_like'],
                                 data['current']['humidity'], data['current']['pressure'],
                                 data['current']['wind_speed'], data['current']['wind_speed'], data['current']['wind_deg'], data['current']['wind_deg'],
                                 data['current']['wind_deg'],
                                 data['current']['clouds'], data['current']['clouds'], data['current']['visibility'], data['cod'],
                                 data['current']['weather'][0]['id'], data['current']['weather'][0]['id'], data['current']['weather'][0]['icon']
                                 )
                            )
                            db.commit()
                            print('added data at ' + str(hour))
                            hour -= 360
                        else:
                            print('error connecting to clean weather api')
                            return
                elif time > hour:
                    # repeated timestamp, delete from db
                    db.execute('DELETE FROM owm_current_weather WHERE timestamp = ?',
                               (time,))
                    db.commit()
        return

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
