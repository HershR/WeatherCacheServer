import os
import json
import requests

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

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
        #dt = datetime.now(timezone.utc)
        # check if city's current weather has
        # already been updated this hour
        #exist = db.execute(
        #    'SELECT * FROM own_current_weather '
        #    'WHERE city_id = ? WHERE BETWEEN timestamp = ?',
        #    (city_id, longitude)
        #).fetchone()

        exclude = "hourly,minutely,daily,alerts"

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
            return data
    return error


@bp.route('/weather/<int:id>/current', methods=('GET', 'POST'))
def current_weather(id):
    #update_current_weather(id)
    db = get_db()

    data = db.execute(
        'SELECT *'
        ' FROM owm_cities c'
        ' JOIN owm_current_weather w ON c.city_id = w.city_id'
    ).fetchall()
    return render_template('weather/currentweather.html', data=data)

@bp.route('/weather/<int:id>/current/dump', methods=('GET', 'POST'))
def current_weather_dump(id):
    # update_current_weather(id)
    db = get_db()
    data = db.execute(
        'SELECT *'
        ' FROM owm_cities c'
        ' JOIN owm_current_weather w ON c.city_id = w.city_id'
    ).fetchall()

    return json.dumps( [dict(weather) for weather in data] ) #CREATE JSON
