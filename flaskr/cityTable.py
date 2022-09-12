import os
import json
import requests
from datetime import timezone
import datetime

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from pprint import pprint
from pyowm.owm import OWM

from werkzeug.exceptions import abort

from flaskr.db import get_db

bp = Blueprint('cityTable', __name__)

#owm = OWM(os.environ.get("OPENWEATHER_API_KEY"))
#reg = owm.city_id_registry()

@bp.route('/')
def index():
    #print('index')
    db = get_db()
    cities = db.execute(
        ' SELECT p.city_id , city_name, city_coord_long, city_coord_lat, city_country' 
        ' FROM owm_cities p'
        ' ORDER BY city_name ASC'
    ).fetchall()
    return render_template('cityTable/index.html', cities=cities)


@bp.route('/search', methods=('GET', 'POST'))
def search():
    if request.method == 'POST':
        #print('call def search in post')
        error = None
        name = str(request.form['city_name']).title()
        # state = str(request.form['state']).title()
        # country = str(request.form['country']).upper()
        if not name:
            error = 'Enter City name'

        if error is None:

            # cities is a list of tuples
            # cities = reg.ids_for(name, country=country, state=state, matching='exact')

            # use geocoding api to find all cities, only returns a max of 5
            url = 'http://api.openweathermap.org/geo/1.0/direct?q={name}&limit=5&appid={key}'\
                .format(name=name, key=os.environ.get("OPENWEATHER_API_KEY"))

            r = requests.get(url)

            if r.status_code!=200:
                error = 'Request failed'
            else:
                cities = r.json()
                data = cities
                for d in data:
                    #pprint(d)
                    if('local_names' in d):
                        del d['local_names']
                return render_template('cityTable/add.html', cities=data)
        if error is not None:
            flash(error)
    #print('call def search in get')
    return render_template('cityTable/search.html')


@bp.route('/addcity/<string:city>', methods=('GET', 'POST'))
def add(city=None):
    data = json.loads(city.replace("\'", "\""))
    error = None
    if not data:
        error = 'city data empty'
    name = str(data['name'])
    country = str(data['country'])
    latitude = data['lat']
    longitude = data['lon']
    if not latitude:
        error += ' missing lat'
    if not longitude:
        error += ' missing long'
    if error is None:
        db = get_db()
        db.execute(
            'INSERT INTO owm_cities (city_name, city_coord_long, city_coord_lat, city_country)'
            ' VALUES (?, ?, ?, ?)',
            (name, longitude, latitude, country)
        )
        db.commit()
        return redirect(url_for('cityTable.index'))

    else:
        flash(error)
    return redirect(url_for('cityTable.search'))


@bp.route('/delete/<int:city_id>', methods=('GET', 'POST'))
def delete(city_id=None):
    return


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


@bp.route('/weather/<int:id>', methods=('GET', 'POST'))
def current_weather(id):
    update_current_weather(id)
    db = get_db()

    data = db.execute(
        'SELECT *'
        ' FROM owm_cities c'
        ' JOIN owm_current_weather w ON c.city_id = w.city_id'
    ).fetchall()
    return render_template('cityTable/currentweather.html', data=data)

