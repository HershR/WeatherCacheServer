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
        ' ORDER BY city_id DESC'
    ).fetchall()
    return render_template('cityTable/index.html', cities=cities)


@bp.route('/search', methods=('GET', 'POST'))
def search():
    if request.method == 'POST':
        print('call def search in post')
        error = None
        name = str(request.form['city_name']).title()
        # state = str(request.form['state']).title()
        # country = str(request.form['country']).upper()
        if not name:
            error = 'Enter City name'

        if error is None:

            # cities is a list of tuples
            # cities = reg.ids_for(name, country=country, state=state, matching='exact')
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
                #return redirect(url_for('cityTable.add', cities=data))
                return render_template('cityTable/addcity.html', cities=data)
        if error is not None:
            print('error flash')
            flash(error)
    print('call def search in get')
    return render_template('cityTable/search.html')


@bp.route('/addcity', methods=('GET', 'POST'))
def add():

    if request.method == 'POST':
        print('def add called in POST')
        citystring = request.form['city']
        city = json.loads(citystring.replace("\'", "\""))
        error = None
        if not city:
            error = 'city data empty'
        print(city)
        latitude = city['lat']
        longitude = city['lon']
        print(latitude)
        print(longitude)
        if not latitude:
            error += ' missing lat'
        if not longitude:
            error += ' missing long'
        print(error)
        if error is None:

            url = "https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude={part}&appid={key}"\
                .format(lat=latitude, lon=longitude, part="hourly,minutely,daily,alerts", key=os.environ.get("OPENWEATHER_API_KEY"))
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                db = get_db()
                db.execute(
                    'INSERT INTO owm_cities (city_name, city_coord_long, city_coord_lat, city_country)'
                    ' VALUES (?, ?, ?, ?)',
                    (city['name'], city['lon'], city['lat'], city['country'])
                )

                #db.execute(
                #    'INSERT INTO owm_current_weather (city_id, city_sun_rise, city_sun_set, timezone, temperature_value )'
                #    ' VALUES ()',
                #    ()
                #)
                db.commit()
                print('added city')
                return redirect(url_for('cityTable.index'))
            else:
                print('status code not 200')
                error = 'Request Error'
        if error is not None:
            print('error flash')
            flash(error)
    print('def add called in GET')
    #pprint(request.args['cities'])
    #return redirect(url_for('cityTable.add', city = request.args['cities']))
    return render_template('cityTable/index.html' )


@bp.route('/<int:id>/current_weather', methods=('GET', 'POST'))
def current_weather(id):
    db = get_db()
    return render_template('cityTable/currentweather.html')